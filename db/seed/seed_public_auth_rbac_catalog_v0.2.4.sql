-- seed_public_auth_rbac_catalog_v0.2.4.sql
-- RBAC catalog seed (roles, permissions, role_permissions)
-- Idempotent. Runs in a single transaction.

BEGIN;

-- 1) Roles catalog
WITH roles(code,name,scope,description) AS (
    VALUES
        ('PLATFORM_ADMIN','Platform Admin','platform','Full platform administration'),
        ('PLATFORM_SECURITY_ADMIN','Platform Security Admin','platform','Platform security administration'),
        ('PLATFORM_AUDITOR','Platform Auditor','platform','Platform audit / read-only'),
        ('PLATFORM_SUPPORT','Platform Support','platform','Platform support (limited)'),

        ('TENANT_ADMIN','Tenant Admin','tenant','Tenant administration'),
        ('TENANT_SECURITY_ADMIN','Tenant Security Admin','tenant','Tenant security administration'),
        ('TENANT_AUDITOR','Tenant Auditor','tenant','Tenant audit / read-only'),
        ('TENANT_REPORT_VIEWER','Tenant Report Viewer','tenant','Reporting / read-only'),
        ('MASTER_DATA_STEWARD','Master Data Steward','tenant','Master data management'),

        ('CAMO_MANAGER','CAMO Manager','domain','CAMO management'),
        ('CAMO_PLANNER','CAMO Planner','domain','CAMO planning'),
        ('CAMO_ENGINEER','CAMO Engineer','domain','CAMO engineering'),
        ('AIRWORTHINESS_REVIEW_STAFF','Airworthiness Review Staff','domain','Airworthiness reviews'),
        ('RELIABILITY_ENGINEER','Reliability Engineer','domain','Reliability engineering'),
        ('TECHNICAL_RECORDS','Technical Records','domain','Tech records / archives'),
        ('AD_SB_ENGINEER','AD/SB Engineer','domain','AD/SB compliance'),
        ('CONFIGURATION_CONTROL','Configuration Control','domain','Configuration / mod status'),
        ('MCC_CONTROLLER','MCC Controller','domain','Maintenance control center'),

        ('MAINT_PLANNER','Maintenance Planner','domain','Maintenance planning'),
        ('PRODUCTION_PLANNER','Production Planner','domain','Production planning'),
        ('LINE_MAINT_SUPERVISOR','Line Maintenance Supervisor','domain','Line maintenance supervision'),
        ('BASE_MAINT_SUPERVISOR','Base Maintenance Supervisor','domain','Base maintenance supervision'),
        ('SHIFT_LEADER','Shift Leader','domain','Shift leadership'),
        ('MECHANIC','Mechanic','domain','Mechanic'),
        ('AVIONICS_TECHNICIAN','Avionics Technician','domain','Avionics'),
        ('STRUCTURES_TECHNICIAN','Structures Technician','domain','Structures'),
        ('ENGINE_TECHNICIAN','Engine Technician','domain','Engines'),
        ('NDT_TECHNICIAN','NDT Technician','domain','NDT'),
        ('COMPONENT_SHOP_TECH','Component Shop Technician','domain','Component shop'),
        ('CABIN_TECH','Cabin Technician','domain','Cabin'),
        ('PAINT_CORROSION_TECH','Paint/Corrosion Technician','domain','Paint & corrosion'),

        ('CERTIFYING_STAFF_CAT_A','Certifying Staff Cat A','domain','CRS category A'),
        ('CERTIFYING_STAFF_CAT_B1','Certifying Staff Cat B1','domain','CRS category B1'),
        ('CERTIFYING_STAFF_CAT_B2','Certifying Staff Cat B2','domain','CRS category B2'),
        ('CERTIFYING_STAFF_CAT_C','Certifying Staff Cat C','domain','CRS category C'),
        ('RELEASE_TO_SERVICE_AUTHORITY','Release to Service Authority','domain','Release to service authority'),

        ('QA_MANAGER','QA Manager','domain','Quality management'),
        ('QC_INSPECTOR','QC Inspector','domain','Quality control / inspection'),
        ('COMPLIANCE_MONITORING','Compliance Monitoring','domain','Compliance monitoring'),
        ('SAFETY_MANAGER','Safety Manager','domain','Safety management'),
        ('TRAINING_ADMIN','Training Admin','domain','Training administration'),
        ('INTERNAL_AUDITOR','Internal Auditor','domain','Internal audit'),

        ('LOGISTICS_OFFICER','Logistics Officer','domain','Logistics operations'),
        ('STORES_RECEIVING','Stores Receiving','domain','Stores receiving'),
        ('STORES_ISSUING','Stores Issuing','domain','Stores issuing'),
        ('INVENTORY_CONTROLLER','Inventory Controller','domain','Inventory control'),
        ('PURCHASING','Purchasing','domain','Purchasing'),
        ('MATERIAL_PLANNER','Material Planner','domain','Material planning'),
        ('SHIPPING','Shipping','domain','Shipping/dispatch'),
        ('TOOL_CRIB','Tool Crib','domain','Tool issuing/returns'),
        ('TOOL_CALIBRATION_CONTROLLER','Tool Calibration Controller','domain','Calibration control'),
        ('DGR_OFFICER','DGR/Hazmat Officer','domain','Dangerous goods / hazmat'),

        ('FINANCE','Finance','domain','Finance operations'),
        ('BILLING_AR','Billing AR','domain','Accounts receivable / invoicing'),
        ('AP_PAYABLES','AP Payables','domain','Accounts payable'),
        ('CONTRACT_MANAGER','Contract Manager','domain','Contracts management'),
        ('CUSTOMER_ACCOUNT_MANAGER','Customer Account Manager','domain','Customer account management'),

        ('PILOT','Pilot','domain','Pilot (basic)'),
        ('CAPTAIN','Captain','domain','Captain'),
        ('FIRST_OFFICER','First Officer','domain','First officer'),
        ('CABIN_CREW','Cabin Crew','domain','Cabin crew'),
        ('FLIGHT_DISPATCH','Flight Dispatch','domain','Flight dispatcher'),
        ('OCC_CONTROLLER','OCC Controller','domain','Operations control center'),

        ('INTEGRATION_SERVICE_ACCOUNT','Integration Service Account','system','System-to-system integration account'),
        ('DATA_EXPORTER','Data Exporter','system','Data export operations'),
        ('DATA_IMPORTER','Data Importer','system','Data import operations')
),
upsert_roles AS (
    INSERT INTO public.auth_roles(code,name,scope,description,is_system)
    SELECT code,name,scope,description,true FROM roles
    ON CONFLICT (code) DO UPDATE
      SET name=EXCLUDED.name,
          scope=EXCLUDED.scope,
          description=EXCLUDED.description,
          updated_at=now()
    RETURNING id, code
)
SELECT count(*) AS roles_upserted FROM upsert_roles;

-- 2) Permissions catalog (NOTE: auth_permissions has no is_system column in migration 0003)
WITH perms(code,domain,description) AS (
    VALUES
        ('platform.tenants.view','platform','platform:tenants:view'),
        ('platform.tenants.create','platform','platform:tenants:create'),
        ('platform.tenants.update','platform','platform:tenants:update'),
        ('platform.tenants.delete','platform','platform:tenants:delete'),
        ('platform.users.view','platform','platform:users:view'),
        ('platform.users.create','platform','platform:users:create'),
        ('platform.users.update','platform','platform:users:update'),
        ('platform.users.disable','platform','platform:users:disable'),
        ('platform.users.reset_password','platform','platform:users:reset_password'),
        ('platform.roles.view','platform','platform:roles:view'),
        ('platform.roles.manage','platform','platform:roles:manage'),
        ('platform.audit.view','platform','platform:audit:view'),
        ('platform.audit.export','platform','platform:audit:export'),
        ('platform.system.view_health','platform','platform:system:view_health'),
        ('platform.system.manage_settings','platform','platform:system:manage_settings'),

        ('tenant.org.view','tenant','tenant:org:view'),
        ('tenant.users.view','tenant','tenant:users:view'),
        ('tenant.users.create','tenant','tenant:users:create'),
        ('tenant.users.update','tenant','tenant:users:update'),
        ('tenant.users.disable','tenant','tenant:users:disable'),
        ('tenant.roles.view','tenant','tenant:roles:view'),
        ('tenant.roles.manage','tenant','tenant:roles:manage'),
        ('tenant.audit.view','tenant','tenant:audit:view'),
        ('tenant.reports.export','tenant','tenant:reports:export'),
        ('tenant.masterdata.import','tenant','tenant:masterdata:import'),

        ('common.dashboard.view','common','common:dashboard:view'),

        ('camo.aircraft.view','camo','camo:aircraft:view'),
        ('camo.aircraft.export','camo','camo:aircraft:export'),
        ('camo.aircraft.assign_mro','camo','camo:aircraft:assign_mro'),
        ('camo.aircraft.update_status','camo','camo:aircraft:update_status'),

        ('camo.airworthiness.view','camo','camo:airworthiness:view'),
        ('camo.airworthiness.plan','camo','camo:airworthiness:plan'),
        ('camo.airworthiness.approve','camo','camo:airworthiness:approve'),
        ('camo.airworthiness.export','camo','camo:airworthiness:export'),

        ('camo.maintenance_program.view','camo','camo:maintenance_program:view'),
        ('camo.maintenance_program.create','camo','camo:maintenance_program:create'),
        ('camo.maintenance_program.update','camo','camo:maintenance_program:update'),
        ('camo.maintenance_program.approve','camo','camo:maintenance_program:approve'),

        ('camo.reliability.view','camo','camo:reliability:view'),
        ('camo.reliability.analyze','camo','camo:reliability:analyze'),
        ('camo.reliability.export','camo','camo:reliability:export'),

        ('camo.ad_sb.view','camo','camo:ad_sb:view'),
        ('camo.ad_sb.assess','camo','camo:ad_sb:assess'),
        ('camo.ad_sb.record_compliance','camo','camo:ad_sb:record_compliance'),
        ('camo.ad_sb.export','camo','camo:ad_sb:export'),

        ('mro.workorders.view','mro','mro:workorders:view'),
        ('mro.workorders.create','mro','mro:workorders:create'),
        ('mro.workorders.update','mro','mro:workorders:update'),
        ('mro.workorders.close','mro','mro:workorders:close'),
        ('mro.signoff.perform','mro','mro:signoff:perform'),
        ('mro.signoff.approve','mro','mro:signoff:approve'),

        ('inv.parts.view','inv','inv:parts:view'),
        ('inv.parts.create','inv','inv:parts:create'),
        ('inv.parts.update','inv','inv:parts:update'),
        ('inv.parts.issue','inv','inv:parts:issue'),
        ('inv.parts.receive','inv','inv:parts:receive'),
        ('inv.parts.import','inv','inv:parts:import'),

        ('qa.audit.view','qa','qa:audit:view'),
        ('qa.audit.create','qa','qa:audit:create'),
        ('qa.audit.close','qa','qa:audit:close'),

        ('fin.invoices.view','fin','fin:invoices:view'),
        ('fin.invoices.create','fin','fin:invoices:create'),
        ('fin.invoices.update','fin','fin:invoices:update'),

        ('ops.atl.view','ops','ops:atl:view'),
        ('ops.atl.create','ops','ops:atl:create'),

        ('int.data.export','int','int:data:export'),
        ('int.data.import','int','int:data:import'),
        ('int.integrations.view','int','int:integrations:view'),
        ('int.integrations.manage','int','int:integrations:manage'),
        ('int.integrations.retry','int','int:integrations:retry'),
        ('int.integrations.export_logs','int','int:integrations:export_logs')
),
upsert_perms AS (
    INSERT INTO public.auth_permissions(code,domain,description)
    SELECT code,domain,description FROM perms
    ON CONFLICT (code) DO UPDATE
      SET domain=EXCLUDED.domain,
          description=EXCLUDED.description,
          updated_at=now()
    RETURNING id, code
)
SELECT count(*) AS perms_upserted FROM upsert_perms;

-- 3) Clear mappings for seeded roles (so catalog stays deterministic)
WITH seeded_roles AS (
    SELECT id FROM public.auth_roles WHERE code IN (
        SELECT code FROM (VALUES
            ('PLATFORM_ADMIN'),('PLATFORM_SECURITY_ADMIN'),('PLATFORM_AUDITOR'),('PLATFORM_SUPPORT'),
            ('TENANT_ADMIN'),('TENANT_SECURITY_ADMIN'),('TENANT_AUDITOR'),('TENANT_REPORT_VIEWER'),('MASTER_DATA_STEWARD'),
            ('CAMO_MANAGER'),('CAMO_PLANNER'),('CAMO_ENGINEER'),('AIRWORTHINESS_REVIEW_STAFF'),('RELIABILITY_ENGINEER'),
            ('TECHNICAL_RECORDS'),('AD_SB_ENGINEER'),('CONFIGURATION_CONTROL'),('MCC_CONTROLLER'),
            ('MAINT_PLANNER'),('PRODUCTION_PLANNER'),('LINE_MAINT_SUPERVISOR'),('BASE_MAINT_SUPERVISOR'),('SHIFT_LEADER'),
            ('MECHANIC'),('AVIONICS_TECHNICIAN'),('STRUCTURES_TECHNICIAN'),('ENGINE_TECHNICIAN'),('NDT_TECHNICIAN'),
            ('COMPONENT_SHOP_TECH'),('CABIN_TECH'),('PAINT_CORROSION_TECH'),
            ('CERTIFYING_STAFF_CAT_A'),('CERTIFYING_STAFF_CAT_B1'),('CERTIFYING_STAFF_CAT_B2'),('CERTIFYING_STAFF_CAT_C'),
            ('RELEASE_TO_SERVICE_AUTHORITY'),
            ('QA_MANAGER'),('QC_INSPECTOR'),('COMPLIANCE_MONITORING'),('SAFETY_MANAGER'),('TRAINING_ADMIN'),('INTERNAL_AUDITOR'),
            ('LOGISTICS_OFFICER'),('STORES_RECEIVING'),('STORES_ISSUING'),('INVENTORY_CONTROLLER'),('PURCHASING'),
            ('MATERIAL_PLANNER'),('SHIPPING'),('TOOL_CRIB'),('TOOL_CALIBRATION_CONTROLLER'),('DGR_OFFICER'),
            ('FINANCE'),('BILLING_AR'),('AP_PAYABLES'),('CONTRACT_MANAGER'),('CUSTOMER_ACCOUNT_MANAGER'),
            ('PILOT'),('CAPTAIN'),('FIRST_OFFICER'),('CABIN_CREW'),('FLIGHT_DISPATCH'),('OCC_CONTROLLER'),
            ('INTEGRATION_SERVICE_ACCOUNT'),('DATA_EXPORTER'),('DATA_IMPORTER')
        ) AS v(code)
    )
),
deleted AS (
    DELETE FROM public.auth_role_permissions rp
    USING seeded_roles r
    WHERE rp.role_id = r.id
    RETURNING 1
)
SELECT count(*) AS mappings_deleted FROM deleted;

-- 4) Role->permission mapping rules (stable, avoids huge VALUES list)
-- Helper: assign permissions by domain prefix
-- PLATFORM_ADMIN: all permissions
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON true
WHERE r.code = 'PLATFORM_ADMIN'
ON CONFLICT DO NOTHING;

-- PLATFORM_SECURITY_ADMIN: platform.* + tenant.roles/manage + tenant.users/manage
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'platform.%' OR p.code IN ('tenant.roles.manage','tenant.users.create','tenant.users.update','tenant.users.disable')
WHERE r.code = 'PLATFORM_SECURITY_ADMIN'
ON CONFLICT DO NOTHING;

-- PLATFORM_AUDITOR: view/export only (platform.*.view + audit.export + tenant.audit.view)
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON
    p.code LIKE 'platform.%.view' OR p.code IN ('platform.audit.export','tenant.audit.view','tenant.reports.export')
WHERE r.code = 'PLATFORM_AUDITOR'
ON CONFLICT DO NOTHING;

-- TENANT_ADMIN: tenant.* + common.*
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'tenant.%' OR p.code LIKE 'common.%'
WHERE r.code = 'TENANT_ADMIN'
ON CONFLICT DO NOTHING;

-- Tenant security/admin subsets
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code IN ('tenant.users.view','tenant.users.create','tenant.users.update','tenant.users.disable','tenant.roles.view','tenant.roles.manage','tenant.audit.view')
WHERE r.code IN ('TENANT_SECURITY_ADMIN','MASTER_DATA_STEWARD')
ON CONFLICT DO NOTHING;

-- CAMO roles
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'camo.%' OR p.code LIKE 'common.%'
WHERE r.code IN ('CAMO_MANAGER','CAMO_PLANNER','CAMO_ENGINEER','AIRWORTHINESS_REVIEW_STAFF','RELIABILITY_ENGINEER','TECHNICAL_RECORDS','AD_SB_ENGINEER','CONFIGURATION_CONTROL','MCC_CONTROLLER')
ON CONFLICT DO NOTHING;

-- MRO roles
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'mro.%' OR p.code LIKE 'common.%'
WHERE r.code IN ('MAINT_PLANNER','PRODUCTION_PLANNER','LINE_MAINT_SUPERVISOR','BASE_MAINT_SUPERVISOR','SHIFT_LEADER','MECHANIC','AVIONICS_TECHNICIAN','STRUCTURES_TECHNICIAN','ENGINE_TECHNICIAN','NDT_TECHNICIAN','COMPONENT_SHOP_TECH','CABIN_TECH','PAINT_CORROSION_TECH')
ON CONFLICT DO NOTHING;

-- Certifying staff: signoff.*
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'mro.signoff.%' OR p.code LIKE 'mro.workorders.%' OR p.code LIKE 'common.%'
WHERE r.code IN ('CERTIFYING_STAFF_CAT_A','CERTIFYING_STAFF_CAT_B1','CERTIFYING_STAFF_CAT_B2','CERTIFYING_STAFF_CAT_C','RELEASE_TO_SERVICE_AUTHORITY')
ON CONFLICT DO NOTHING;

-- Logistics / inventory
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'inv.%' OR p.code LIKE 'common.%'
WHERE r.code IN ('LOGISTICS_OFFICER','STORES_RECEIVING','STORES_ISSUING','INVENTORY_CONTROLLER','PURCHASING','MATERIAL_PLANNER','SHIPPING','TOOL_CRIB','TOOL_CALIBRATION_CONTROLLER','DGR_OFFICER','DATA_IMPORTER')
ON CONFLICT DO NOTHING;

-- QA
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'qa.%' OR p.code LIKE 'common.%'
WHERE r.code IN ('QA_MANAGER','QC_INSPECTOR','COMPLIANCE_MONITORING','SAFETY_MANAGER','TRAINING_ADMIN','INTERNAL_AUDITOR')
ON CONFLICT DO NOTHING;

-- Finance
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'fin.%' OR p.code LIKE 'common.%'
WHERE r.code IN ('FINANCE','BILLING_AR','AP_PAYABLES','CONTRACT_MANAGER','CUSTOMER_ACCOUNT_MANAGER')
ON CONFLICT DO NOTHING;

-- Ops (flight/cabin)
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'ops.%' OR p.code LIKE 'common.%'
WHERE r.code IN ('PILOT','CAPTAIN','FIRST_OFFICER','CABIN_CREW','FLIGHT_DISPATCH','OCC_CONTROLLER')
ON CONFLICT DO NOTHING;

-- Integrations / export
INSERT INTO public.auth_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM public.auth_roles r
JOIN public.auth_permissions p ON p.code LIKE 'int.%' OR p.code IN ('platform.audit.export','tenant.reports.export','common.dashboard.view')
WHERE r.code IN ('INTEGRATION_SERVICE_ACCOUNT','DATA_EXPORTER')
ON CONFLICT DO NOTHING;

COMMIT;
