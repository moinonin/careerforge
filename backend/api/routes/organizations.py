"""Organization management API routes — Sprint 7.

Implements:
- Organization CRUD with team billing (seat_price_cents, team_quota)
- Invitation system (OrganizationInvitation with tokens)
- Master profile sharing (OrganizationMasterProfile)
- Team usage tracking (OrganizationUsageLog)
- Team quota management (pooled monthly generation quota)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user, get_db
from backend.models import (
    Organization, OrganizationMember, OrganizationInvitation,
    OrganizationMasterProfile, OrganizationUsageLog, User, AuditLog,
)
from backend.security import generate_token_hash

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


# ─── Request/Response Models ───────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str
    max_seats: int = 5
    seat_price_cents: int = 1200  # $12/seat/month


class OrganizationResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    max_seats: int
    used_storage_bytes: int
    seat_price_cents: int
    team_quota: int
    team_quota_used: int
    created_at: str
    quota_period_start: str

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str | None
    role: str
    joined_at: str


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "member"  # admin | member


class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    role: str
    token: str
    expires_at: str
    status: str
    created_at: str


class InvitationAccept(BaseModel):
    token: str


class MasterProfileCreate(BaseModel):
    title: str
    profile_data: dict
    is_shared: bool = True


class MasterProfileResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    profile_data: dict
    is_shared: bool
    created_by: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    organization_id: str
    member_count: int
    max_seats: int
    available_seats: int
    used_storage_bytes: int
    team_quota: int
    team_quota_used: int
    available_generations: int
    quota_period_start: str
    subscription_status: str
    plan_tier: str
    generations_this_month: int


# ─── Helpers ───────────────────────────────────────────────────────────

async def get_org_member(
    org_id: str, user_id: str, db: AsyncSession, required_role: str | None = None
) -> OrganizationMember:
    """Get membership and verify access."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if required_role and member.role != required_role:
        raise HTTPException(status_code=403, detail=f"Requires {required_role} role")
    return member


# ─── Routes ────────────────────────────────────────────────────────────

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new organization (user becomes owner/admin)."""
    org = Organization(
        name=data.name,
        owner_id=current_user.id,
        max_seats=data.max_seats,
        seat_price_cents=data.seat_price_cents,
        team_quota=250,  # Default team plan quota
    )
    db.add(org)
    await db.flush()

    # Add creator as admin member
    member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role="admin",
    )
    db.add(member)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        owner_id=org.owner_id,
        max_seats=org.max_seats,
        used_storage_bytes=org.used_storage_bytes,
        seat_price_cents=org.seat_price_cents,
        team_quota=org.team_quota,
        team_quota_used=org.team_quota_used,
        created_at=org.created_at.isoformat(),
        quota_period_start=org.quota_period_start.isoformat() if org.quota_period_start else "",
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get organization details (members only)."""
    await get_org_member(org_id, current_user.id, db)
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        owner_id=org.owner_id,
        max_seats=org.max_seats,
        used_storage_bytes=org.used_storage_bytes,
        seat_price_cents=org.seat_price_cents,
        team_quota=org.team_quota,
        team_quota_used=org.team_quota_used,
        created_at=org.created_at.isoformat(),
        quota_period_start=org.quota_period_start.isoformat() if org.quota_period_start else "",
    )


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List organization members (members only)."""
    await get_org_member(org_id, current_user.id, db)
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == org_id)
    )
    members = []
    for member, user in result.all():
        members.append(
            MemberResponse(
                id=member.id,
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=member.role,
                joined_at=member.joined_at.isoformat() if member.joined_at else "",
            )
        )
    return members


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a member from the organization (admin only)."""
    await get_org_member(org_id, current_user.id, db, required_role="admin")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(member)
    await db.commit()


# ─── Invitations ───────────────────────────────────────────────────────

@router.post("/{org_id}/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: str,
    data: InvitationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Invite a user to the organization (admin only)."""
    await get_org_member(org_id, current_user.id, db, required_role="admin")

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check seat limit
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == org_id)
    )
    member_count = len(result.scalars().all())
    if member_count >= org.max_seats:
        raise HTTPException(status_code=400, detail="Organization seat limit reached")

    # Create invitation record
    token = generate_token_hash(32)
    expires_at = datetime.now(UTC) + timedelta(days=7)
    invitation = OrganizationInvitation(
        organization_id=org_id,
        email=data.email,
        role=data.role,
        token=token,
        invited_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(invitation)

    # Log the invitation
    audit = AuditLog(
        actor_id=current_user.id,
        action="organization.invite",
        details=f"Invited {data.email} to organization {org_id} with role {data.role}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(invitation)

    return InvitationResponse(
        id=invitation.id,
        organization_id=org_id,
        email=invitation.email,
        role=invitation.role,
        token=invitation.token,
        expires_at=invitation.expires_at.isoformat(),
        status=invitation.status,
        created_at=invitation.created_at.isoformat(),
    )


@router.post("/invitations/accept")
async def accept_invitation(
    data: InvitationAccept,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Accept an organization invitation by token."""
    result = await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token == data.token,
            OrganizationInvitation.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found or already accepted")

    if invitation.expires_at < datetime.now(UTC):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=410, detail="Invitation has expired")

    result = await db.execute(
        select(Organization).where(Organization.id == invitation.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check seat limit
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == invitation.organization_id)
    )
    member_count = len(result.scalars().all())
    if member_count >= org.max_seats:
        raise HTTPException(status_code=400, detail="Organization seat limit reached")

    # Check if user is already a member
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == invitation.organization_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    if result.scalar_one_or_none():
        invitation.status = "cancelled"
        await db.commit()
        raise HTTPException(status_code=400, detail="You are already a member of this organization")

    # Add user as member
    member = OrganizationMember(
        organization_id=invitation.organization_id,
        user_id=current_user.id,
        role=invitation.role,
        invited_by=invitation.invited_by,
    )
    db.add(member)

    # Mark invitation as accepted
    invitation.status = "accepted"
    await db.commit()

    return {"message": f"Successfully joined {org.name}", "role": invitation.role}


# ─── Master Profiles ──────────────────────────────────────────────────

@router.post("/{org_id}/master-profiles", response_model=MasterProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_master_profile(
    org_id: str,
    data: MasterProfileCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a shared master profile template (admin only)."""
    await get_org_member(org_id, current_user.id, db, required_role="admin")

    profile = OrganizationMasterProfile(
        organization_id=org_id,
        title=data.title,
        profile_data=data.profile_data,
        created_by=current_user.id,
        is_shared=data.is_shared,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return MasterProfileResponse(
        id=profile.id,
        organization_id=profile.organization_id,
        title=profile.title,
        profile_data=profile.profile_data,
        is_shared=profile.is_shared,
        created_by=profile.created_by,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


@router.get("/{org_id}/master-profiles", response_model=list[MasterProfileResponse])
async def list_master_profiles(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List shared master profiles for an organization (members only)."""
    await get_org_member(org_id, current_user.id, db)
    result = await db.execute(
        select(OrganizationMasterProfile).where(
            OrganizationMasterProfile.organization_id == org_id,
            OrganizationMasterProfile.is_shared == True,
        ).order_by(OrganizationMasterProfile.created_at.desc())
    )
    profiles = result.scalars().all()
    return [
        MasterProfileResponse(
            id=p.id,
            organization_id=p.organization_id,
            title=p.title,
            profile_data=p.profile_data,
            is_shared=p.is_shared,
            created_by=p.created_by,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in profiles
    ]


@router.delete("/{org_id}/master-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_master_profile(
    org_id: str,
    profile_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a master profile template (admin only)."""
    await get_org_member(org_id, current_user.id, db, required_role="admin")

    result = await db.execute(
        select(OrganizationMasterProfile).where(
            OrganizationMasterProfile.id == profile_id,
            OrganizationMasterProfile.organization_id == org_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Master profile not found")

    await db.delete(profile)
    await db.commit()


# ─── Usage Tracking ────────────────────────────────────────────────────

@router.post("/{org_id}/usage/log")
async def log_generation_usage(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Log a generation for team quota tracking (called after each generation)."""
    await get_org_member(org_id, current_user.id, db)

    period_key = datetime.now(UTC).strftime("%Y-%m")

    # Check if a log entry already exists for this user this period
    result = await db.execute(
        select(OrganizationUsageLog).where(
            OrganizationUsageLog.organization_id == org_id,
            OrganizationUsageLog.user_id == current_user.id,
            OrganizationUsageLog.period_key == period_key,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.generation_count += 1
        existing.updated_at = datetime.now(UTC)
    else:
        log_entry = OrganizationUsageLog(
            organization_id=org_id,
            user_id=current_user.id,
            generation_count=1,
            period_key=period_key,
        )
        db.add(log_entry)

    # Update organization's used quota
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if org:
        org.team_quota_used += 1

    await db.commit()
    return {"message": "Usage logged", "period_key": period_key}


@router.get("/{org_id}/usage", response_model=UsageResponse)
async def get_org_usage(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get organization usage stats (admin only)."""
    await get_org_member(org_id, current_user.id, db, required_role="admin")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Count members
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == org_id)
    )
    member_count = len(result.scalars().all())

    # Get subscription info
    from backend.models import Subscription
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == org_id)
    )
    subscription = result.scalar_one_or_none()

    # Get this month's generation count from usage log
    period_key = datetime.now(UTC).strftime("%Y-%m")
    result = await db.execute(
        select(func.sum(OrganizationUsageLog.generation_count)).where(
            OrganizationUsageLog.organization_id == org_id,
            OrganizationUsageLog.period_key == period_key,
        )
    )
    generations_this_month = result.scalar_one_or_none() or 0

    available_seats = org.max_seats - member_count
    available_generations = org.team_quota - org.team_quota_used

    return UsageResponse(
        organization_id=org_id,
        member_count=member_count,
        max_seats=org.max_seats,
        available_seats=available_seats,
        used_storage_bytes=org.used_storage_bytes,
        team_quota=org.team_quota,
        team_quota_used=org.team_quota_used,
        available_generations=max(0, available_generations),
        quota_period_start=org.quota_period_start.isoformat() if org.quota_period_start else "",
        subscription_status=subscription.status if subscription else "none",
        plan_tier=subscription.plan_tier if subscription else "none",
        generations_this_month=generations_this_month,
    )


@router.post("/{org_id}/usage/reset")
async def reset_quota(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reset team quota for new period (admin only)."""
    await get_org_member(org_id, current_user.id, db, required_role="admin")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.team_quota_used = 0
    org.quota_period_start = datetime.now(UTC)
    await db.commit()
    return {"message": "Quota reset for new period", "team_quota_used": 0}


# ─── Team Billing ──────────────────────────────────────────────────────

@router.patch("/{org_id}/billing")
async def update_billing(
    org_id: str,
    data: BaseModel,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update team billing configuration (admin only)."""
    await get_org_member(org_id, current_user.id, db, required_role="admin")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # In production, this would integrate with Stripe
    # For now, return the current billing state
    return {
        "organization_id": org_id,
        "seat_price_cents": org.seat_price_cents,
        "max_seats": org.max_seats,
        "team_quota": org.team_quota,
        "team_quota_used": org.team_quota_used,
        "subscription_status": "active",  # Would come from Stripe
        "next_payment_cents": org.seat_price_cents * org.max_seats,  # per-month estimate
    }