-- Deal Desk Orchestrator: Phase 1C Schema V2 (24 tables)
-- PostgreSQL 15+; design implementation, 28 September 2026.
-- Apply to an empty database or dedicated schema. See schema-validation-notes.md.
-- All monetary amounts are EUR; IDs and codes are synthetic/validated by loaders.

BEGIN;
CREATE SCHEMA IF NOT EXISTS deal_desk;
SET search_path TO deal_desk, public;

-- 1. A product_id denotes one immutable catalogue version.
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_code TEXT NOT NULL,
    catalog_version TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    product_type TEXT NOT NULL CHECK (product_type IN ('physical','software','subscription','service','component')),
    attributes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    list_price NUMERIC(14,2) NOT NULL,
    standard_cost NUMERIC(14,2) NOT NULL,
    billing_model TEXT NOT NULL,
    unit_of_measure TEXT NOT NULL CHECK (unit_of_measure IN ('device','device_year','user_year','licence_year','instance_month','protected_tb_month','service_month','service_package','coverage_year','each','component_unit')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_sellable BOOLEAN NOT NULL,
    fulfillment_mode TEXT NOT NULL,
    stock_uom TEXT NOT NULL,
    UNIQUE (product_code, catalog_version),
    UNIQUE (product_id, catalog_version),
    CHECK (btrim(product_code) <> '' AND btrim(catalog_version) <> ''),
    CHECK (jsonb_typeof(attributes_json) = 'object'),
    CHECK (list_price >= 0 AND standard_cost >= 0),
    CHECK (NOT is_active OR NOT is_sellable OR list_price > 0),
    CHECK (NOT (fulfillment_mode = 'component') OR (NOT is_sellable AND standard_cost > 0 AND stock_uom <> 'not_applicable')),
    CHECK (billing_model IN ('one_time','recurring','usage_based','fixed_service_fee','not_applicable')),
    CHECK (billing_model <> 'not_applicable' OR NOT is_sellable),
    CHECK (fulfillment_mode IN ('stocked_finished','supplier_finished','make_to_order','digital_activation','scheduled_service','component')),
    CHECK (stock_uom IN ('each','component_unit','not_applicable')),
    CHECK ((fulfillment_mode IN ('digital_activation','scheduled_service')) = (stock_uom = 'not_applicable'))
);

-- 2. Customer identity is separate from credit and invoices.
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_code TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    size_segment TEXT NOT NULL CHECK (size_segment IN ('SMB','Mid-Market','Enterprise')),
    strategic_account BOOLEAN NOT NULL DEFAULT FALSE,
    industry TEXT NOT NULL,
    country_code CHAR(2) NOT NULL,
    region TEXT NOT NULL,
    customer_since DATE NOT NULL,
    account_status TEXT NOT NULL CHECK (account_status IN ('Active','Inactive','Suspended','Blocked'))
);

-- 3. Shared supplier identity for offers and PO headers.
CREATE TABLE suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_code TEXT NOT NULL UNIQUE,
    supplier_name TEXT NOT NULL,
    country_code CHAR(2) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','inactive')),
    order_calendar_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (jsonb_typeof(order_calendar_json) = 'object')
);

-- 4-6. Versioned commercial rule representations; configuration is source of values.
CREATE TABLE pricing_rules (
    pricing_rule_id TEXT PRIMARY KEY,
    policy_set_code TEXT NOT NULL CHECK (policy_set_code IN ('BASELINE_2026','LENIENT_EXPERIMENT','STRICT_EXPERIMENT')),
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('volume_discount','segment_discount','category_margin_floor')),
    scope_type TEXT NOT NULL CHECK (scope_type IN ('global','product','category','segment','region')),
    scope_value TEXT,
    condition_json JSONB NOT NULL,
    action_json JSONB NOT NULL,
    priority INTEGER NOT NULL,
    is_stackable BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (jsonb_typeof(condition_json) = 'object' AND jsonb_typeof(action_json) = 'object'),
    CHECK ((scope_type = 'global') = (scope_value IS NULL))
);

CREATE TABLE policy_rules (
    policy_rule_id TEXT PRIMARY KEY,
    policy_set_code TEXT NOT NULL CHECK (policy_set_code IN ('BASELINE_2026','LENIENT_EXPERIMENT','STRICT_EXPERIMENT')),
    rule_name TEXT NOT NULL,
    policy_area TEXT NOT NULL CHECK (policy_area IN ('pricing','margin','payment','contract','credit','delivery')),
    scope_type TEXT NOT NULL CHECK (scope_type IN ('global','product','category','segment','region')),
    scope_value TEXT,
    condition_json JSONB NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info','warning','approval_required','blocker')),
    required_action TEXT NOT NULL CHECK (required_action IN ('continue','request_exception','escalate','reject')),
    explanation_template TEXT NOT NULL,
    priority INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (jsonb_typeof(condition_json) = 'object'),
    CHECK ((scope_type = 'global') = (scope_value IS NULL)),
    CHECK (severity <> 'blocker' OR required_action = 'reject')
);

CREATE TABLE approval_rules (
    approval_rule_id TEXT PRIMARY KEY,
    policy_set_code TEXT NOT NULL CHECK (policy_set_code IN ('BASELINE_2026','LENIENT_EXPERIMENT','STRICT_EXPERIMENT')),
    rule_name TEXT NOT NULL,
    condition_json JSONB NOT NULL,
    required_role TEXT NOT NULL CHECK (required_role IN ('Regional_Manager','Sales_Director','Sales_VP','Finance_Director','Legal_Compliance')),
    approval_sequence INTEGER NOT NULL CHECK (approval_sequence >= 0),
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (jsonb_typeof(condition_json) = 'object')
);

-- 7. Product-specific rules reference the same technical catalogue version.
CREATE TABLE compatibility_rules (
    compatibility_rule_id TEXT PRIMARY KEY,
    catalog_version TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('requires_product','excludes_product','attribute_constraint','required_deal_field','installation_eligibility')),
    scope_type TEXT NOT NULL CHECK (scope_type IN ('line','configured_group','whole_deal')),
    source_product_id TEXT,
    target_product_id TEXT,
    condition_json JSONB NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('warning','blocker')),
    message TEXT NOT NULL,
    priority INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (source_product_id, catalog_version) REFERENCES products(product_id, catalog_version),
    FOREIGN KEY (target_product_id, catalog_version) REFERENCES products(product_id, catalog_version),
    CHECK (jsonb_typeof(condition_json) = 'object'),
    CHECK (source_product_id IS NULL OR source_product_id IS DISTINCT FROM target_product_id),
    CHECK (rule_type NOT IN ('requires_product','excludes_product') OR (source_product_id IS NOT NULL AND target_product_id IS NOT NULL))
);

-- 8-9. Configured bill of materials. Temporal overlap needs a trigger below.
CREATE TABLE bom_headers (
    bom_id TEXT PRIMARY KEY,
    finished_product_id TEXT NOT NULL,
    catalog_version TEXT NOT NULL,
    bom_version TEXT NOT NULL,
    configuration_signature_json JSONB NOT NULL,
    output_quantity NUMERIC(14,3) NOT NULL CHECK (output_quantity > 0),
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('active','inactive')),
    FOREIGN KEY (finished_product_id, catalog_version) REFERENCES products(product_id, catalog_version),
    UNIQUE (finished_product_id, catalog_version, bom_version, configuration_signature_json),
    CHECK (jsonb_typeof(configuration_signature_json) = 'object'),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE bom_lines (
    bom_line_id TEXT PRIMARY KEY,
    bom_id TEXT NOT NULL REFERENCES bom_headers(bom_id),
    component_product_id TEXT NOT NULL REFERENCES products(product_id),
    required_quantity_per_output NUMERIC(14,3) NOT NULL CHECK (required_quantity_per_output > 0),
    scrap_pct NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (scrap_pct >= 0 AND scrap_pct < 100),
    substitute_group_code TEXT,
    priority INTEGER NOT NULL CHECK (priority >= 0),
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (bom_id, component_product_id),
    CHECK (substitute_group_code IS NULL OR btrim(substitute_group_code) <> '')
);

-- 10-12. Credit, current AR and observed payment events are distinct.
CREATE TABLE customer_credit_profiles (
    customer_id TEXT PRIMARY KEY REFERENCES customers(customer_id),
    credit_limit NUMERIC(14,2) NOT NULL CHECK (credit_limit > 0),
    unbilled_committed_amount NUMERIC(14,2) NOT NULL CHECK (unbilled_committed_amount >= 0),
    commitments_as_of_at TIMESTAMPTZ NOT NULL,
    commitment_evidence_ref TEXT NOT NULL,
    risk_rating TEXT NOT NULL CHECK (risk_rating IN ('Low','Medium','High')),
    credit_status TEXT NOT NULL CHECK (credit_status IN ('Active','Review','On-Hold')),
    default_payment_terms_days INTEGER NOT NULL CHECK (default_payment_terms_days IN (15,30,45,60,90)),
    last_review_date DATE NOT NULL,
    next_review_date DATE,
    CHECK (next_review_date IS NULL OR next_review_date >= last_review_date)
);

CREATE TABLE accounts_receivable (
    receivable_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    invoice_number TEXT NOT NULL UNIQUE,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    original_amount NUMERIC(14,2) NOT NULL CHECK (original_amount > 0),
    outstanding_amount NUMERIC(14,2) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Open','Partially Paid','Overdue','Paid')),
    as_of_date DATE NOT NULL,
    CHECK (invoice_date <= due_date AND invoice_date <= as_of_date),
    CHECK (outstanding_amount >= 0 AND outstanding_amount <= original_amount),
    CHECK ((status = 'Paid') = (outstanding_amount = 0)),
    CHECK (status <> 'Partially Paid' OR outstanding_amount < original_amount),
    CHECK (status <> 'Overdue' OR (due_date < as_of_date AND outstanding_amount > 0))
);

CREATE TABLE payment_history (
    payment_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    invoice_number TEXT NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    paid_date DATE NOT NULL,
    invoice_amount NUMERIC(14,2) NOT NULL CHECK (invoice_amount > 0),
    paid_amount NUMERIC(14,2) NOT NULL CHECK (paid_amount > 0),
    CHECK (invoice_date <= due_date AND paid_date >= invoice_date),
    CHECK (paid_amount <= invoice_amount)
);

-- 13. Existing reservations are aggregate allocated quantities.
CREATE TABLE inventory (
    inventory_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    location_id TEXT NOT NULL,
    quantity_on_hand NUMERIC(14,3) NOT NULL,
    quantity_allocated NUMERIC(14,3) NOT NULL DEFAULT 0,
    snapshot_at TIMESTAMPTZ NOT NULL,
    UNIQUE (product_id, location_id, snapshot_at),
    CHECK (quantity_on_hand >= 0 AND quantity_allocated >= 0 AND quantity_allocated <= quantity_on_hand)
);

-- 14-16. Offers, committed PO headers and dated incoming quantities.
CREATE TABLE supplier_items (
    supplier_item_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    supplier_sku TEXT NOT NULL,
    minimum_order_qty NUMERIC(14,3) NOT NULL CHECK (minimum_order_qty > 0),
    order_multiple NUMERIC(14,3) NOT NULL CHECK (order_multiple > 0),
    lead_days_min INTEGER NOT NULL,
    lead_days_mode INTEGER NOT NULL,
    lead_days_max INTEGER NOT NULL,
    unit_cost NUMERIC(14,2) NOT NULL CHECK (unit_cost > 0),
    currency_code CHAR(3) NOT NULL DEFAULT 'EUR' CHECK (currency_code = 'EUR'),
    valid_from DATE NOT NULL,
    valid_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (supplier_id, product_id, valid_from),
    CHECK (lead_days_min >= 0 AND lead_days_min <= lead_days_mode AND lead_days_mode <= lead_days_max),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE TABLE purchase_orders (
    purchase_order_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    reference_number TEXT NOT NULL UNIQUE,
    ordered_at TIMESTAMPTZ NOT NULL,
    confirmed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('Draft','Placed','Confirmed','Delayed','Cancelled','Received')),
    destination_location_id TEXT NOT NULL,
    CHECK (confirmed_at IS NULL OR confirmed_at >= ordered_at),
    CHECK (status NOT IN ('Confirmed','Delayed','Received') OR confirmed_at IS NOT NULL)
);

CREATE TABLE inbound_supply (
    supply_id TEXT PRIMARY KEY,
    purchase_order_id TEXT REFERENCES purchase_orders(purchase_order_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    location_id TEXT NOT NULL,
    quantity NUMERIC(14,3) NOT NULL CHECK (quantity > 0),
    quantity_allocated NUMERIC(14,3) NOT NULL DEFAULT 0,
    expected_date DATE NOT NULL,
    confirmed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('Planned','Confirmed','Delayed','Cancelled')),
    reference_number TEXT NOT NULL UNIQUE,
    evidence_ref TEXT,
    valid_until TIMESTAMPTZ,
    CHECK (quantity_allocated >= 0 AND quantity_allocated <= quantity),
    CHECK (status <> 'Confirmed' OR (confirmed_at IS NOT NULL AND (purchase_order_id IS NOT NULL OR evidence_ref IS NOT NULL))),
    CHECK (valid_until IS NULL OR (confirmed_at IS NOT NULL AND valid_until > confirmed_at))
);

-- 17-18. Resource need per operation and day-level allocated capacity.
CREATE TABLE production_requirements (
    requirement_id TEXT PRIMARY KEY,
    bom_id TEXT NOT NULL REFERENCES bom_headers(bom_id),
    operation_seq INTEGER NOT NULL CHECK (operation_seq >= 1),
    capability_code TEXT NOT NULL,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('equipment','workforce')),
    setup_hours NUMERIC(10,3) NOT NULL CHECK (setup_hours >= 0),
    hours_per_unit NUMERIC(10,3) NOT NULL CHECK (hours_per_unit >= 0),
    batch_size INTEGER NOT NULL CHECK (batch_size > 0),
    status TEXT NOT NULL CHECK (status IN ('active','inactive')),
    UNIQUE (bom_id, operation_seq, capability_code, resource_type),
    CHECK (setup_hours > 0 OR hours_per_unit > 0)
);

CREATE TABLE production_capacity (
    capacity_id TEXT PRIMARY KEY,
    location_id TEXT NOT NULL,
    capability_code TEXT NOT NULL,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('equipment','workforce')),
    capacity_date DATE NOT NULL,
    time_zone TEXT NOT NULL,
    available_capacity_hours NUMERIC(10,3) NOT NULL,
    allocated_capacity_hours NUMERIC(10,3) NOT NULL DEFAULT 0,
    snapshot_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','unavailable')),
    evidence_ref TEXT NOT NULL,
    UNIQUE (location_id, capability_code, resource_type, capacity_date, snapshot_at),
    CHECK (available_capacity_hours >= 0 AND allocated_capacity_hours >= 0 AND allocated_capacity_hours <= available_capacity_hours),
    CHECK (status <> 'unavailable' OR available_capacity_hours = 0)
);

-- 19. Digital pools are neither warehouse stock nor shipping promises.
CREATE TABLE digital_capacity (
    digital_capacity_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    configuration_signature_json JSONB NOT NULL,
    provider_id TEXT REFERENCES suppliers(supplier_id),
    region_code TEXT NOT NULL,
    term_code TEXT NOT NULL,
    capacity_unit TEXT NOT NULL CHECK (capacity_unit IN ('user','licence','instance','protected_tb')),
    capacity_total NUMERIC(14,3) NOT NULL,
    quantity_allocated NUMERIC(14,3) NOT NULL DEFAULT 0,
    activation_lead_days INTEGER NOT NULL CHECK (activation_lead_days >= 0),
    commitment_status TEXT NOT NULL CHECK (commitment_status IN ('binding','provisional','unknown')),
    confirmed_at TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    snapshot_at TIMESTAMPTZ NOT NULL,
    evidence_ref TEXT,
    CHECK (jsonb_typeof(configuration_signature_json) = 'object'),
    CHECK (capacity_total >= 0 AND quantity_allocated >= 0 AND quantity_allocated <= capacity_total),
    CHECK (commitment_status <> 'binding' OR (confirmed_at IS NOT NULL AND evidence_ref IS NOT NULL AND valid_until IS NOT NULL)),
    CHECK (valid_until IS NULL OR (confirmed_at IS NOT NULL AND valid_until > confirmed_at))
);
-- A NULL provider_id denotes an internal pool; COALESCE prevents duplicates for it.
CREATE UNIQUE INDEX digital_capacity_pool_snapshot_uniq ON digital_capacity
    (product_id, configuration_signature_json, region_code, term_code, capacity_unit,
     (coalesce(provider_id, '[internal]')), snapshot_at);

-- 20. Delivery lane cutoffs use origin-local time, not server UTC.
CREATE TABLE shipping_lanes (
    lane_id TEXT PRIMARY KEY,
    origin_location_id TEXT NOT NULL,
    origin_time_zone TEXT NOT NULL,
    destination_country_code CHAR(2) NOT NULL,
    destination_region TEXT NOT NULL,
    shipping_service_code TEXT NOT NULL CHECK (shipping_service_code IN ('standard','express')),
    transit_workdays INTEGER NOT NULL CHECK (transit_workdays >= 0),
    dispatch_weekdays_json JSONB NOT NULL,
    cutoff_local_time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (jsonb_typeof(dispatch_weekdays_json) = 'array')
);
CREATE UNIQUE INDEX shipping_lanes_active_uniq ON shipping_lanes
    (origin_location_id, destination_country_code, destination_region, shipping_service_code)
    WHERE is_active;

-- 21-22. One immutable submitted header with many configured line items.
CREATE TABLE deals (
    deal_id TEXT PRIMARY KEY,
    supersedes_deal_id TEXT REFERENCES deals(deal_id),
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    salesperson_id TEXT NOT NULL,
    deal_name TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    currency_code CHAR(3) NOT NULL DEFAULT 'EUR' CHECK (currency_code = 'EUR'),
    catalog_version TEXT NOT NULL,
    policy_set_code TEXT NOT NULL CHECK (policy_set_code IN ('BASELINE_2026','LENIENT_EXPERIMENT','STRICT_EXPERIMENT')),
    requested_delivery_date DATE,
    destination_country_code CHAR(2),
    destination_region TEXT,
    shipping_service_code TEXT CHECK (shipping_service_code IN ('standard','express')),
    terms_json JSONB NOT NULL,
    exception_justification TEXT,
    requirements_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_refs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    salesperson_comments TEXT,
    deal_status TEXT NOT NULL CHECK (deal_status IN ('Draft','Submitted','Under Review','Approved','Rejected','Cancelled')),
    dataset_type TEXT NOT NULL CHECK (dataset_type IN ('historical','generated_test','evaluation')),
    historical_decision TEXT CHECK (historical_decision IN ('Approved','Rejected')),
    decision_reason TEXT,
    approved_by_roles_json JSONB,
    UNIQUE (deal_id, policy_set_code, catalog_version),
    CHECK (supersedes_deal_id IS NULL OR supersedes_deal_id <> deal_id),
    CHECK (jsonb_typeof(terms_json) = 'object' AND jsonb_typeof(requirements_json) = 'object'),
    CHECK (jsonb_typeof(evidence_refs_json) = 'array'),
    CHECK (approved_by_roles_json IS NULL OR jsonb_typeof(approved_by_roles_json) = 'array'),
    CHECK (NOT (terms_json ? 'payment_method')),
    CHECK (dataset_type = 'historical' OR (historical_decision IS NULL AND decision_reason IS NULL AND approved_by_roles_json IS NULL))
);

CREATE TABLE deal_lines (
    deal_line_id TEXT PRIMARY KEY,
    deal_id TEXT NOT NULL REFERENCES deals(deal_id),
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    quoted_unit_price NUMERIC(14,2) NOT NULL CHECK (quoted_unit_price > 0),
    configuration_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    fulfillment_group_code TEXT,
    requested_activation_date DATE,
    installation_requested BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (deal_id, line_number),
    CHECK (jsonb_typeof(configuration_json) = 'object'),
    CHECK (fulfillment_group_code IS NULL OR btrim(fulfillment_group_code) <> '')
);

-- 23. Multiple immutable runs can replay one deal under commercial profiles.
CREATE TABLE deal_runs (
    run_id UUID PRIMARY KEY,
    deal_id TEXT NOT NULL,
    original_policy_set_code TEXT NOT NULL,
    applied_policy_set_code TEXT NOT NULL CHECK (applied_policy_set_code IN ('BASELINE_2026','LENIENT_EXPERIMENT','STRICT_EXPERIMENT')),
    catalog_version_used TEXT NOT NULL,
    as_of_at TIMESTAMPTZ NOT NULL,
    data_snapshot_ref TEXT NOT NULL,
    input_snapshot_json JSONB NOT NULL,
    config_hash TEXT NOT NULL,
    run_status TEXT NOT NULL CHECK (run_status IN ('queued','running','completed','stopped','failed')),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (deal_id, original_policy_set_code, catalog_version_used)
      REFERENCES deals(deal_id, policy_set_code, catalog_version),
    UNIQUE (run_id, deal_id, applied_policy_set_code, catalog_version_used),
    CHECK (as_of_at <= started_at AND (completed_at IS NULL OR completed_at >= started_at)),
    CHECK (jsonb_typeof(input_snapshot_json) = 'object'),
    CHECK (run_status NOT IN ('completed','stopped','failed') OR completed_at IS NOT NULL)
);

-- 24. Attempts log attribution to the frozen run context.
CREATE TABLE agent_execution_log (
    execution_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    run_id UUID NOT NULL,
    deal_id TEXT NOT NULL,
    agent_name TEXT NOT NULL CHECK (agent_name IN ('Configuration','Pricing','Availability','Credit','Policy','Approval','Orchestrator')),
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('Running','Success','Failed','Retried','Skipped')),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    error_message TEXT,
    input_snapshot_json JSONB NOT NULL,
    output_json JSONB,
    flags_json JSONB,
    reasoning_summary TEXT,
    model_name TEXT,
    prompt_version TEXT,
    applied_policy_set_code TEXT NOT NULL,
    catalog_version_used TEXT NOT NULL,
    FOREIGN KEY (run_id, deal_id, applied_policy_set_code, catalog_version_used)
      REFERENCES deal_runs(run_id, deal_id, applied_policy_set_code, catalog_version_used),
    UNIQUE (run_id, agent_name, attempt_number),
    CHECK (completed_at IS NULL OR completed_at >= started_at),
    CHECK (jsonb_typeof(input_snapshot_json) = 'object'),
    CHECK (output_json IS NULL OR jsonb_typeof(output_json) = 'object'),
    CHECK (flags_json IS NULL OR jsonb_typeof(flags_json) IN ('object','array')),
    CHECK ((status = 'Running') = (completed_at IS NULL))
);

-- Selective indexes support latest-as-of snapshots and agent evidence lookups.
CREATE INDEX deal_lines_product_idx ON deal_lines(product_id);
CREATE INDEX deal_runs_deal_asof_idx ON deal_runs(deal_id, as_of_at DESC);
CREATE INDEX agent_execution_log_run_idx ON agent_execution_log(run_id, agent_name);
CREATE INDEX accounts_receivable_customer_snapshot_idx ON accounts_receivable(customer_id, as_of_date, due_date);
CREATE INDEX payment_history_customer_invoice_idx ON payment_history(customer_id, invoice_number, paid_date);
CREATE INDEX inventory_product_location_snapshot_idx ON inventory(product_id, location_id, snapshot_at DESC);
CREATE INDEX inbound_supply_product_location_eta_idx ON inbound_supply(product_id, location_id, expected_date) WHERE status = 'Confirmed';
CREATE INDEX supplier_items_product_validity_idx ON supplier_items(product_id, valid_from, valid_to) WHERE is_active;
CREATE INDEX production_capacity_day_idx ON production_capacity(location_id, capability_code, resource_type, capacity_date, snapshot_at DESC);
CREATE INDEX digital_capacity_product_region_idx ON digital_capacity(product_id, region_code, term_code, snapshot_at DESC);
CREATE INDEX bom_headers_product_effective_idx ON bom_headers(finished_product_id, effective_from, effective_to) WHERE status = 'active';

-- Checks that cannot be expressed with a row-local CHECK or simple FK.
CREATE FUNCTION validate_bom_header() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE product_mode TEXT; sellable BOOLEAN;
BEGIN
    SELECT p.fulfillment_mode, p.is_sellable INTO product_mode, sellable
      FROM products p WHERE p.product_id = NEW.finished_product_id;
    IF product_mode IS DISTINCT FROM 'make_to_order' OR NOT sellable THEN
        RAISE EXCEPTION 'BOM % must produce a sellable make-to-order product', NEW.bom_id;
    END IF;
    -- Serialize competing inserts for the same product/configuration.
    PERFORM pg_advisory_xact_lock(hashtextextended(
      NEW.finished_product_id || ':' || NEW.configuration_signature_json::text, 0));
    IF NEW.status = 'active' AND EXISTS (
       SELECT 1 FROM bom_headers b
        WHERE b.bom_id <> NEW.bom_id
          AND b.finished_product_id = NEW.finished_product_id
          AND b.catalog_version = NEW.catalog_version
          AND b.configuration_signature_json = NEW.configuration_signature_json
          AND b.status = 'active'
          AND tstzrange(b.effective_from,b.effective_to,'[)') &&
              tstzrange(NEW.effective_from,NEW.effective_to,'[)')
    ) THEN
        RAISE EXCEPTION 'overlapping effective BOM for product %', NEW.finished_product_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER bom_header_guard BEFORE INSERT OR UPDATE ON bom_headers
FOR EACH ROW EXECUTE FUNCTION validate_bom_header();

CREATE FUNCTION validate_bom_line() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_product TEXT; parent_version TEXT; component_version TEXT;
        component_mode TEXT; component_sellable BOOLEAN;
BEGIN
    SELECT b.finished_product_id, b.catalog_version INTO parent_product, parent_version
      FROM bom_headers b WHERE b.bom_id = NEW.bom_id;
    SELECT p.catalog_version, p.fulfillment_mode, p.is_sellable
      INTO component_version, component_mode, component_sellable
      FROM products p WHERE p.product_id = NEW.component_product_id;
    IF NEW.component_product_id = parent_product OR component_version IS DISTINCT FROM parent_version
       OR component_mode IS DISTINCT FROM 'component' OR component_sellable THEN
        RAISE EXCEPTION 'BOM % has invalid or mismatched component %', NEW.bom_id, NEW.component_product_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER bom_line_guard BEFORE INSERT OR UPDATE ON bom_lines
FOR EACH ROW EXECUTE FUNCTION validate_bom_line();

CREATE FUNCTION validate_operational_product_mode() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE product_mode TEXT;
BEGIN
    SELECT fulfillment_mode INTO product_mode FROM products WHERE product_id = NEW.product_id;
    IF TG_TABLE_NAME = 'digital_capacity' THEN
        IF product_mode IS DISTINCT FROM 'digital_activation' THEN
            RAISE EXCEPTION 'digital pool % must reference a digital-activation product', NEW.digital_capacity_id;
        END IF;
    ELSIF product_mode NOT IN ('stocked_finished','supplier_finished','make_to_order','component') THEN
        RAISE EXCEPTION 'physical supply table % cannot reference product mode %', TG_TABLE_NAME, product_mode;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER inventory_product_guard BEFORE INSERT OR UPDATE OF product_id ON inventory
FOR EACH ROW EXECUTE FUNCTION validate_operational_product_mode();
CREATE TRIGGER inbound_product_guard BEFORE INSERT OR UPDATE OF product_id ON inbound_supply
FOR EACH ROW EXECUTE FUNCTION validate_operational_product_mode();
CREATE TRIGGER supplier_item_product_guard BEFORE INSERT OR UPDATE OF product_id ON supplier_items
FOR EACH ROW EXECUTE FUNCTION validate_operational_product_mode();
CREATE TRIGGER digital_product_guard BEFORE INSERT OR UPDATE OF product_id ON digital_capacity
FOR EACH ROW EXECUTE FUNCTION validate_operational_product_mode();

CREATE FUNCTION validate_origin_time_zone() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE requested_zone TEXT;
BEGIN
    requested_zone := CASE WHEN TG_TABLE_NAME = 'shipping_lanes'
                           THEN to_jsonb(NEW)->>'origin_time_zone'
                           ELSE to_jsonb(NEW)->>'time_zone' END;
    IF NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name = requested_zone) THEN
        RAISE EXCEPTION 'unknown IANA time zone %', requested_zone;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER shipping_time_zone_guard BEFORE INSERT OR UPDATE OF origin_time_zone ON shipping_lanes
FOR EACH ROW EXECUTE FUNCTION validate_origin_time_zone();
CREATE TRIGGER production_time_zone_guard BEFORE INSERT OR UPDATE OF time_zone ON production_capacity
FOR EACH ROW EXECUTE FUNCTION validate_origin_time_zone();

CREATE FUNCTION validate_inbound_commitment() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE header purchase_orders%ROWTYPE;
BEGIN
    IF NEW.status = 'Confirmed' AND NEW.purchase_order_id IS NULL AND
       (NEW.evidence_ref IS NULL OR btrim(NEW.evidence_ref) = '') THEN
        RAISE EXCEPTION 'confirmed inbound % requires binding evidence', NEW.supply_id;
    END IF;
    IF NEW.purchase_order_id IS NOT NULL THEN
        SELECT * INTO header FROM purchase_orders WHERE purchase_order_id = NEW.purchase_order_id;
        IF header.destination_location_id IS DISTINCT FROM NEW.location_id THEN
            RAISE EXCEPTION 'receipt location differs from PO %', NEW.purchase_order_id;
        END IF;
        IF NEW.status = 'Confirmed' AND
          (header.status NOT IN ('Confirmed','Delayed') OR header.confirmed_at IS NULL OR
           NEW.confirmed_at < header.confirmed_at) THEN
            RAISE EXCEPTION 'confirmed inbound % lacks effective PO commitment', NEW.supply_id;
        END IF;
        IF header.status IN ('Cancelled','Received') AND NEW.status = 'Confirmed' THEN
            RAISE EXCEPTION 'received/cancelled PO % has active confirmed receipt', NEW.purchase_order_id;
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER inbound_commitment_guard BEFORE INSERT OR UPDATE ON inbound_supply
FOR EACH ROW EXECUTE FUNCTION validate_inbound_commitment();

CREATE FUNCTION validate_po_status() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IN ('Cancelled','Received') AND EXISTS (
       SELECT 1 FROM inbound_supply i WHERE i.purchase_order_id = NEW.purchase_order_id
         AND i.status = 'Confirmed'
    ) THEN
        RAISE EXCEPTION 'PO % still has active confirmed receipt', NEW.purchase_order_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER po_status_guard BEFORE UPDATE OF status ON purchase_orders
FOR EACH ROW EXECUTE FUNCTION validate_po_status();

CREATE FUNCTION validate_deal_header() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE term_months TEXT;
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.deal_status <> 'Draft' AND NEW.deal_status = 'Draft' THEN
        RAISE EXCEPTION 'submitted deal % cannot return to Draft', OLD.deal_id;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.deal_status <> 'Draft' AND
       (to_jsonb(NEW) - ARRAY['deal_status','historical_decision','decision_reason','approved_by_roles_json'])
       IS DISTINCT FROM
       (to_jsonb(OLD) - ARRAY['deal_status','historical_decision','decision_reason','approved_by_roles_json']) THEN
        RAISE EXCEPTION 'submitted deal % inputs are immutable; resubmit with supersedes_deal_id', OLD.deal_id;
    END IF;
    IF NEW.supersedes_deal_id IS NOT NULL AND EXISTS (
      WITH RECURSIVE predecessor(id) AS (
        SELECT NEW.supersedes_deal_id
        UNION
        SELECT d.supersedes_deal_id FROM deals d
          JOIN predecessor p ON d.deal_id = p.id
          WHERE d.supersedes_deal_id IS NOT NULL
      )
      SELECT 1 FROM predecessor WHERE id = NEW.deal_id
    ) THEN
        RAISE EXCEPTION 'resubmission chain for deal % contains a cycle', NEW.deal_id;
    END IF;
    IF NEW.deal_status = 'Draft' THEN RETURN NEW; END IF;
    IF jsonb_typeof(NEW.terms_json->'payment_terms_days') IS DISTINCT FROM 'number' OR
       (NEW.terms_json->>'payment_terms_days') NOT IN ('15','30','45','60','90') THEN
        RAISE EXCEPTION 'deal % requires an allowed payment_terms_days value', NEW.deal_id;
    END IF;
    IF jsonb_typeof(NEW.terms_json->'allow_partial_delivery') IS DISTINCT FROM 'boolean' THEN
        RAISE EXCEPTION 'deal % requires boolean allow_partial_delivery', NEW.deal_id;
    END IF;
    IF jsonb_typeof(NEW.terms_json->'contract_clause_codes') IS DISTINCT FROM 'array' THEN
        RAISE EXCEPTION 'deal % requires contract_clause_codes array', NEW.deal_id;
    END IF;
    IF jsonb_array_length(NEW.terms_json->'contract_clause_codes') = 0 OR EXISTS (
       SELECT 1 FROM jsonb_array_elements_text(NEW.terms_json->'contract_clause_codes') c(code)
         WHERE c.code IS NULL OR c.code NOT IN ('standard','preapproved_variant','legal_review','prohibited')
    ) THEN
        RAISE EXCEPTION 'deal % has invalid contract clause codes', NEW.deal_id;
    END IF;
    IF NEW.terms_json ? 'contract_months' THEN
        term_months := NEW.terms_json->>'contract_months';
        IF jsonb_typeof(NEW.terms_json->'contract_months') <> 'number'
           OR term_months !~ '^[1-9][0-9]*$' THEN
            RAISE EXCEPTION 'deal % has invalid contract_months', NEW.deal_id;
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER deal_header_guard BEFORE INSERT OR UPDATE ON deals
FOR EACH ROW EXECUTE FUNCTION validate_deal_header();

CREATE FUNCTION validate_deal_line() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent deals%ROWTYPE; p products%ROWTYPE;
BEGIN
    IF TG_OP = 'UPDATE' AND EXISTS (
       SELECT 1 FROM deals d WHERE d.deal_id = OLD.deal_id AND d.deal_status <> 'Draft'
    ) THEN
        RAISE EXCEPTION 'cannot move or edit a line from submitted deal %', OLD.deal_id;
    END IF;
    SELECT * INTO parent FROM deals WHERE deal_id = CASE WHEN TG_OP = 'DELETE' THEN OLD.deal_id ELSE NEW.deal_id END;
    IF parent.deal_status <> 'Draft' THEN
        RAISE EXCEPTION 'submitted deal % lines are immutable', parent.deal_id;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    SELECT * INTO p FROM products WHERE product_id = NEW.product_id;
    IF p.catalog_version IS DISTINCT FROM parent.catalog_version OR NOT p.is_active OR NOT p.is_sellable THEN
        RAISE EXCEPTION 'line % uses unavailable or wrong-version product', NEW.deal_line_id;
    END IF;
    IF NEW.requested_activation_date IS NOT NULL AND p.fulfillment_mode <> 'digital_activation' THEN
        RAISE EXCEPTION 'activation date only applies to digital lines';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER deal_line_guard BEFORE INSERT OR UPDATE OR DELETE ON deal_lines
FOR EACH ROW EXECUTE FUNCTION validate_deal_line();

-- Deferred so a transaction may finish inserting lines before submitting its header.
CREATE FUNCTION check_submitted_deal() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d deals%ROWTYPE; physical BOOLEAN; install_requested BOOLEAN;
        line_record RECORD; months INTEGER; units INTEGER; expected_units INTEGER;
BEGIN
    SELECT * INTO d FROM deals WHERE deal_id = NEW.deal_id;
    IF d.deal_status = 'Draft' THEN RETURN NULL; END IF;
    IF NOT EXISTS (SELECT 1 FROM deal_lines WHERE deal_id = d.deal_id) THEN
        RAISE EXCEPTION 'submitted deal % has no lines', d.deal_id;
    END IF;
    SELECT coalesce(bool_or(p.fulfillment_mode IN
           ('stocked_finished','supplier_finished','make_to_order')),FALSE),
           coalesce(bool_or(l.installation_requested),FALSE)
      INTO physical, install_requested
      FROM deal_lines l JOIN products p USING (product_id) WHERE l.deal_id = d.deal_id;
    IF physical AND (d.requested_delivery_date IS NULL OR d.shipping_service_code IS NULL) THEN
        RAISE EXCEPTION 'physical deal % needs requested arrival and shipping service', d.deal_id;
    END IF;
    IF (physical OR install_requested) AND
      (d.destination_country_code IS NULL OR d.destination_region IS NULL) THEN
        RAISE EXCEPTION 'deal % needs delivery/installation destination', d.deal_id;
    END IF;
    FOR line_record IN
      SELECT l.deal_line_id, l.quantity, l.configuration_json, p.billing_model, p.unit_of_measure
      FROM deal_lines l JOIN products p ON p.product_id = l.product_id
      WHERE l.deal_id = d.deal_id AND p.billing_model = 'recurring'
    LOOP
        IF NOT (d.terms_json ? 'contract_months') OR
           jsonb_typeof(line_record.configuration_json->'units_per_period') IS DISTINCT FROM 'number' OR
           (line_record.configuration_json->>'units_per_period') !~ '^[1-9][0-9]*$' THEN
            RAISE EXCEPTION 'recurring line % needs contract_months and positive units_per_period', line_record.deal_line_id;
        END IF;
        months := (d.terms_json->>'contract_months')::integer;
        units := (line_record.configuration_json->>'units_per_period')::integer;
        IF line_record.unit_of_measure IN ('instance_month','protected_tb_month','service_month') THEN
            expected_units := units * months;
        ELSIF line_record.unit_of_measure IN ('device_year','user_year','licence_year','coverage_year') THEN
            IF months % 12 <> 0 THEN
                RAISE EXCEPTION 'annual line % requires a multiple-of-12-month term', line_record.deal_line_id;
            END IF;
            expected_units := units * (months / 12);
        ELSE
            RAISE EXCEPTION 'recurring line % has unsupported billable unit %', line_record.deal_line_id, line_record.unit_of_measure;
        END IF;
        IF line_record.quantity <> expected_units THEN
            RAISE EXCEPTION 'recurring line % quantity mismatches full-term units', line_record.deal_line_id;
        END IF;
    END LOOP;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER submitted_deal_check
AFTER INSERT OR UPDATE ON deals DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION check_submitted_deal();

CREATE FUNCTION freeze_run_context() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE deal_submitted_at TIMESTAMPTZ; deal_status_at_run TEXT;
BEGIN
    IF TG_OP = 'UPDATE' AND
      (to_jsonb(NEW) - ARRAY['run_status','completed_at']) IS DISTINCT FROM
      (to_jsonb(OLD) - ARRAY['run_status','completed_at']) THEN
        RAISE EXCEPTION 'run % input/config context is immutable', OLD.run_id;
    END IF;
    SELECT submitted_at, deal_status INTO deal_submitted_at, deal_status_at_run
      FROM deals WHERE deal_id = NEW.deal_id;
    IF deal_status_at_run = 'Draft' OR NEW.started_at < deal_submitted_at THEN
        RAISE EXCEPTION 'run % precedes submission or references a draft', NEW.run_id;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER deal_run_context_guard BEFORE INSERT OR UPDATE ON deal_runs
FOR EACH ROW EXECUTE FUNCTION freeze_run_context();

-- A restricted repository may use this view for operational deal inputs.
-- Do not grant base deals SELECT to agent-facing database roles.
CREATE VIEW agent_visible_deals AS SELECT
    deal_id, supersedes_deal_id, customer_id, salesperson_id, deal_name,
    submitted_at, currency_code, catalog_version, policy_set_code,
    requested_delivery_date, destination_country_code, destination_region,
    shipping_service_code, terms_json, exception_justification,
    requirements_json, evidence_refs_json, salesperson_comments
FROM deals;

COMMIT;
