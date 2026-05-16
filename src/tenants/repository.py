import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.tenants.models import Tenant, User, TenantMember

logger = logging.getLogger(__name__)


class TenantRepository:
    """CRUD operations for tenants, users, and tenant memberships."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an active AsyncSession."""
        self._session = session

    async def create_tenant(self, name: str, slug: str) -> Tenant:
        """Create a new tenant.
        
        Args:
            name: Display name of the tenant
            slug: URL-safe identifier (must be unique)
            
        Returns:
            Created Tenant instance
        """
        tenant = Tenant(id=str(uuid.uuid4()), name=name, slug=slug)
        self._session.add(tenant)
        await self._session.flush()
        logger.info("Created tenant", extra={"slug": slug, "tenant_id": tenant.id})
        return tenant

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Retrieve active tenant by slug.
        
        Args:
            slug: The tenant slug
            
        Returns:
            Tenant if found and active, None otherwise
        """
        result = await self._session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve active tenant by ID.
        
        Args:
            tenant_id: The tenant UUID
            
        Returns:
            Tenant if found and active, None otherwise
        """
        result = await self._session.execute(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def create_user(
        self, email: str, display_name: str, hashed_password: str
    ) -> User:
        """Create a new user.
        
        Args:
            email: User email (must be unique)
            display_name: User display name
            hashed_password: Pre-hashed password
            
        Returns:
            Created User instance
        """
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            display_name=display_name,
            hashed_password=hashed_password,
        )
        self._session.add(user)
        await self._session.flush()
        logger.info("Created user", extra={"email": email, "user_id": user.id})
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve active user by email.
        
        Args:
            email: The user email
            
        Returns:
            User if found and active, None otherwise
        """
        result = await self._session.execute(
            select(User).where(User.email == email, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve active user by ID.
        
        Args:
            user_id: The user UUID
            
        Returns:
            User if found and active, None otherwise
        """
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def add_member(
        self, tenant_id: str, user_id: str, role: str = "member"
    ) -> TenantMember:
        """Add a user to a tenant with a specific role.
        
        Args:
            tenant_id: The tenant UUID
            user_id: The user UUID
            role: Membership role ('owner', 'admin', 'member')
            
        Returns:
            Created TenantMember instance
        """
        member = TenantMember(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        self._session.add(member)
        await self._session.flush()
        logger.info(
            "Added tenant member",
            extra={"tenant_id": tenant_id, "user_id": user_id, "role": role},
        )
        return member

    async def get_member(
        self, tenant_id: str, user_id: str
    ) -> Optional[TenantMember]:
        """Retrieve a user's membership in a specific tenant.
        
        Args:
            tenant_id: The tenant UUID
            user_id: The user UUID
            
        Returns:
            TenantMember if found, None otherwise
        """
        result = await self._session.execute(
            select(TenantMember).where(
                TenantMember.tenant_id == tenant_id,
                TenantMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
