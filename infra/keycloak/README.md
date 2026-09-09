# Keycloak Configuration

This directory contains the auto-provisioned realm configuration for Keycloak.

**Important Architectural Note:**
Keycloak carries authentication only. No realm/client roles encode tenant-scoped roles (e.g. `institution_admin`, `department_head`, `reviewer`, `faculty`). 

Each test identity's tenant-scoped role is seeded as a `staff_profile` row (identity_id + tenant_id + roles array) in the demo seed script, and is **not** configured in Keycloak. 

Keycloak's only role-like concept here is the `platform_super_admin` flag on `identity.platform_role`, which is also set directly in seed data for that one test identity, not derived from any Keycloak claim.
