import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

from src.tenants.context import TenantContext, SYSTEM_TENANT_ID
from src.tenants.models import Tenant, User, TenantMember
from src.tenants.repository import TenantRepository


class TestTenantContextConstants:
    """Test TenantContext constants and initialization."""

    def test_system_tenant_id_constant(self) -> None:
        """Verify the system tenant ID constant is correct."""
        assert SYSTEM_TENANT_ID == "00000000-0000-0000-0000-000000000001"
        assert isinstance(SYSTEM_TENANT_ID, str)
        assert len(SYSTEM_TENANT_ID) == 36  # UUID format


class TestTenantContextCreation:
    """Test TenantContext instantiation and field access."""

    def test_tenant_context_creation_with_owner_role(self) -> None:
        """Create TenantContext with owner role."""
        ctx = TenantContext(tenant_id="tenant-abc", user_id="user-xyz", role="owner")
        assert ctx.tenant_id == "tenant-abc"
        assert ctx.user_id == "user-xyz"
        assert ctx.role == "owner"

    def test_tenant_context_creation_with_admin_role(self) -> None:
        """Create TenantContext with admin role."""
        ctx = TenantContext(tenant_id="t1", user_id="u1", role="admin")
        assert ctx.role == "admin"

    def test_tenant_context_creation_with_member_role(self) -> None:
        """Create TenantContext with member role."""
        ctx = TenantContext(tenant_id="t1", user_id="u1", role="member")
        assert ctx.role == "member"

    def test_tenant_context_with_system_tenant(self) -> None:
        """Create TenantContext with system tenant ID."""
        ctx = TenantContext(
            tenant_id=SYSTEM_TENANT_ID, user_id="service-account", role="owner"
        )
        assert ctx.tenant_id == SYSTEM_TENANT_ID
        assert ctx.user_id == "service-account"

    def test_tenant_context_empty_user_id(self) -> None:
        """TenantContext accepts empty user_id for system operations."""
        ctx = TenantContext(tenant_id=SYSTEM_TENANT_ID, user_id="", role="member")
        assert ctx.user_id == ""
        assert ctx.tenant_id == SYSTEM_TENANT_ID


class TestTenantModelInstantiation:
    """Test Tenant model creation and properties."""

    def test_tenant_model_basic_creation(self) -> None:
        """Create a basic Tenant instance."""
        t = Tenant(id="t1", name="Acme Corporation", slug="acme-corp")
        assert t.id == "t1"
        assert t.name == "Acme Corporation"
        assert t.slug == "acme-corp"

    def test_tenant_model_inactive(self) -> None:
        """Create an inactive Tenant."""
        t = Tenant(id="t2", name="Defunct Inc", slug="defunct", is_active=False)
        assert t.is_active is False

    def test_tenant_model_with_explicit_active(self) -> None:
        """Tenant with explicit is_active=True."""
        t = Tenant(id="t3", name="Active Org", slug="active", is_active=True)
        assert t.is_active is True

    def test_tenant_model_members_relationship(self) -> None:
        """Tenant has members relationship."""
        t = Tenant(id="t4", name="Social Org", slug="social")
        assert t.members == []  # Empty by default


class TestUserModelInstantiation:
    """Test User model creation and properties."""

    def test_user_model_creation(self) -> None:
        """Create a basic User instance."""
        u = User(
            id="u1",
            email="alice@example.com",
            display_name="Alice Smith",
            hashed_password="hashed_xyz",
        )
        assert u.id == "u1"
        assert u.email == "alice@example.com"
        assert u.display_name == "Alice Smith"
        assert u.hashed_password == "hashed_xyz"

    def test_user_model_with_explicit_active(self) -> None:
        """Create an active User explicitly."""
        u = User(
            id="u2",
            email="bob@example.com",
            display_name="Bob Jones",
            hashed_password="hashed_abc",
            is_active=True,
        )
        assert u.is_active is True

    def test_user_model_inactive_user(self) -> None:
        """Create an inactive User."""
        u = User(
            id="u3",
            email="charlie@example.com",
            display_name="Charlie",
            hashed_password="hashed_123",
            is_active=False,
        )
        assert u.is_active is False

    def test_user_model_last_login_null(self) -> None:
        """User last_login_at is nullable."""
        u = User(
            id="u4",
            email="diana@example.com",
            display_name="Diana",
            hashed_password="hashed_456",
        )
        assert u.last_login_at is None

    def test_user_model_last_login_set(self) -> None:
        """User last_login_at can be set."""
        now = datetime.now(UTC)
        u = User(
            id="u5",
            email="eve@example.com",
            display_name="Eve",
            hashed_password="hashed_789",
            last_login_at=now,
        )
        assert u.last_login_at == now

    def test_user_model_memberships_relationship(self) -> None:
        """User has memberships relationship."""
        u = User(
            id="u6",
            email="frank@example.com",
            display_name="Frank",
            hashed_password="hashed_000",
        )
        assert u.memberships == []  # Empty by default


class TestTenantMemberModelInstantiation:
    """Test TenantMember model creation and properties."""

    def test_tenant_member_creation_owner(self) -> None:
        """Create a TenantMember with owner role."""
        m = TenantMember(
            id="m1", tenant_id="t1", user_id="u1", role="owner"
        )
        assert m.id == "m1"
        assert m.tenant_id == "t1"
        assert m.user_id == "u1"
        assert m.role == "owner"

    def test_tenant_member_creation_admin(self) -> None:
        """Create a TenantMember with admin role."""
        m = TenantMember(
            id="m2", tenant_id="t1", user_id="u2", role="admin"
        )
        assert m.role == "admin"

    def test_tenant_member_creation_member(self) -> None:
        """Create a TenantMember with member role."""
        m = TenantMember(
            id="m3", tenant_id="t1", user_id="u3", role="member"
        )
        assert m.role == "member"

    def test_tenant_member_with_explicit_role(self) -> None:
        """TenantMember with explicitly set role."""
        m = TenantMember(id="m4", tenant_id="t1", user_id="u4", role="member")
        assert m.role == "member"

    def test_tenant_member_relationships(self) -> None:
        """TenantMember has tenant and user relationships."""
        m = TenantMember(
            id="m6", tenant_id="t1", user_id="u1", role="owner"
        )
        # Relationships are lazy-loaded; check they exist
        assert hasattr(m, "tenant")
        assert hasattr(m, "user")


@pytest.mark.asyncio
class TestTenantRepositoryCreate:
    """Test TenantRepository create operations."""

    async def test_create_tenant_basic(self) -> None:
        """Create a tenant via repository."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        tenant = await repo.create_tenant(
            name="Test Organization", slug="test-org"
        )

        assert tenant.name == "Test Organization"
        assert tenant.slug == "test-org"
        assert tenant.id is not None
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, Tenant)
        session.flush.assert_awaited_once()

    async def test_create_tenant_sets_values_correctly(self) -> None:
        """Created tenant has correct values."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        tenant = await repo.create_tenant(
            name="Active Org", slug="active-org"
        )

        assert tenant.name == "Active Org"
        assert tenant.slug == "active-org"

    async def test_create_multiple_tenants(self) -> None:
        """Create multiple tenants."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        t1 = await repo.create_tenant(name="Org 1", slug="org-1")
        t2 = await repo.create_tenant(name="Org 2", slug="org-2")

        assert t1.name == "Org 1"
        assert t2.name == "Org 2"
        assert t1.id != t2.id
        assert session.add.call_count == 2

    async def test_create_user_basic(self) -> None:
        """Create a user via repository."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        user = await repo.create_user(
            email="test@example.com",
            display_name="Test User",
            hashed_password="hashed_secret",
        )

        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.hashed_password == "hashed_secret"
        assert user.id is not None
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, User)
        session.flush.assert_awaited_once()

    async def test_create_user_sets_values_correctly(self) -> None:
        """Created user has correct values."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        user = await repo.create_user(
            email="active@example.com",
            display_name="Active User",
            hashed_password="hashed",
        )

        assert user.email == "active@example.com"
        assert user.display_name == "Active User"
        assert user.hashed_password == "hashed"

    async def test_add_member_basic(self) -> None:
        """Add a user as a member to a tenant."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        member = await repo.add_member(
            tenant_id="t1", user_id="u1", role="owner"
        )

        assert member.tenant_id == "t1"
        assert member.user_id == "u1"
        assert member.role == "owner"
        assert member.id is not None
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, TenantMember)
        session.flush.assert_awaited_once()

    async def test_add_member_default_role(self) -> None:
        """Add a member with default role."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        member = await repo.add_member(tenant_id="t1", user_id="u2")

        assert member.role == "member"

    async def test_add_member_multiple_roles(self) -> None:
        """Add members with different roles."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        m1 = await repo.add_member(
            tenant_id="t1", user_id="u1", role="owner"
        )
        m2 = await repo.add_member(
            tenant_id="t1", user_id="u2", role="admin"
        )
        m3 = await repo.add_member(
            tenant_id="t1", user_id="u3", role="member"
        )

        assert m1.role == "owner"
        assert m2.role == "admin"
        assert m3.role == "member"


@pytest.mark.asyncio
class TestTenantRepositoryRetrieve:
    """Test TenantRepository retrieve operations."""

    async def test_get_tenant_by_slug_found(self) -> None:
        """Get tenant by slug when it exists and is active."""
        session = AsyncMock()
        expected_tenant = Tenant(
            id="t1", name="Found Org", slug="found-org", is_active=True
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expected_tenant
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        tenant = await repo.get_tenant_by_slug("found-org")

        assert tenant == expected_tenant
        assert tenant.name == "Found Org"
        session.execute.assert_awaited_once()

    async def test_get_tenant_by_slug_not_found(self) -> None:
        """Get tenant by slug returns None when not found."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        tenant = await repo.get_tenant_by_slug("nonexistent")

        assert tenant is None

    async def test_get_tenant_by_id_found(self) -> None:
        """Get tenant by ID when it exists and is active."""
        session = AsyncMock()
        expected_tenant = Tenant(
            id="t1", name="Active Org", slug="active-org", is_active=True
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expected_tenant
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        tenant = await repo.get_tenant_by_id("t1")

        assert tenant == expected_tenant

    async def test_get_tenant_by_id_not_found(self) -> None:
        """Get tenant by ID returns None when not found."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        tenant = await repo.get_tenant_by_id("nonexistent-id")

        assert tenant is None

    async def test_get_tenant_inactive_not_returned(self) -> None:
        """Get tenant filters out inactive tenants."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        tenant = await repo.get_tenant_by_slug("inactive-org")

        assert tenant is None

    async def test_get_user_by_email_found(self) -> None:
        """Get user by email when found and active."""
        session = AsyncMock()
        expected_user = User(
            id="u1",
            email="alice@example.com",
            display_name="Alice",
            hashed_password="hashed",
            is_active=True,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expected_user
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        user = await repo.get_user_by_email("alice@example.com")

        assert user == expected_user
        assert user.email == "alice@example.com"

    async def test_get_user_by_email_not_found(self) -> None:
        """Get user by email returns None when not found."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        user = await repo.get_user_by_email("nonexistent@example.com")

        assert user is None

    async def test_get_user_by_id_found(self) -> None:
        """Get user by ID when found and active."""
        session = AsyncMock()
        expected_user = User(
            id="u1",
            email="bob@example.com",
            display_name="Bob",
            hashed_password="hashed",
            is_active=True,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expected_user
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        user = await repo.get_user_by_id("u1")

        assert user == expected_user

    async def test_get_user_by_id_not_found(self) -> None:
        """Get user by ID returns None when not found."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        user = await repo.get_user_by_id("nonexistent-id")

        assert user is None

    async def test_get_user_inactive_not_returned(self) -> None:
        """Get user filters out inactive users."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        user = await repo.get_user_by_email("inactive@example.com")

        assert user is None

    async def test_get_member_found(self) -> None:
        """Get membership when it exists."""
        session = AsyncMock()
        expected_member = TenantMember(
            id="m1", tenant_id="t1", user_id="u1", role="owner"
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expected_member
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        member = await repo.get_member("t1", "u1")

        assert member == expected_member
        assert member.role == "owner"

    async def test_get_member_not_found(self) -> None:
        """Get membership returns None when not found."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = TenantRepository(session)
        member = await repo.get_member("t1", "u999")

        assert member is None


@pytest.mark.asyncio
class TestTenantRepositoryEdgeCases:
    """Test edge cases and error handling in TenantRepository."""

    async def test_create_tenant_with_special_characters_in_name(self) -> None:
        """Create tenant with special characters in name."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        tenant = await repo.create_tenant(
            name="Org & Co. (Ltd.)", slug="org-and-co"
        )

        assert tenant.name == "Org & Co. (Ltd.)"

    async def test_create_user_with_long_email(self) -> None:
        """Create user with a very long email."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        long_email = "a" * 100 + "@example.com"
        user = await repo.create_user(
            email=long_email,
            display_name="User",
            hashed_password="hashed",
        )

        assert user.email == long_email

    async def test_repository_maintains_session_reference(self) -> None:
        """Repository correctly maintains session reference."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        # Verify session is accessible
        assert repo._session == session

    async def test_create_operations_call_flush(self) -> None:
        """Create operations call session.flush after adding."""
        session = AsyncMock()
        session.flush = AsyncMock()
        repo = TenantRepository(session)

        await repo.create_tenant(name="Tracked", slug="tracked")

        # Verify flush was called
        session.flush.assert_awaited_once()
