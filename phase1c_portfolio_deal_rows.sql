-- One fictional submitted workstation deal tied to BOM-001 and the supply slice.
-- Loaded only inside a disposable PostgreSQL test transaction.
SET search_path TO deal_desk, public;
INSERT INTO customers (customer_id, customer_code, customer_name, size_segment,
    strategic_account, industry, country_code, region, customer_since, account_status)
VALUES ('SYN-CUST-WORKSTATION', 'SYN-CUST-WORKSTATION', 'Fictional Workshop Buyer',
        'SMB', FALSE, 'manufacturing', 'DE', 'DE-NW', '2025-01-01', 'Active');
INSERT INTO customer_credit_profiles (customer_id, credit_limit, unbilled_committed_amount,
    commitments_as_of_at, commitment_evidence_ref, risk_rating, credit_status,
    default_payment_terms_days, last_review_date, next_review_date)
VALUES ('SYN-CUST-WORKSTATION', 10000, 0, '2026-10-07T09:00:00Z',
        'SYN-CREDIT-SNAPSHOT', 'Low', 'Active', 30, '2026-10-01', '2027-01-01');
INSERT INTO shipping_lanes (lane_id, origin_location_id, origin_time_zone,
    destination_country_code, destination_region, shipping_service_code,
    transit_workdays, dispatch_weekdays_json, cutoff_local_time, is_active)
VALUES ('SYN-LANE-WORKSTATION', 'WH-EU-CENTRAL', 'Europe/Berlin',
        'DE', 'DE-NW', 'standard', 2, '[1,2,3,4,5]', '15:00:00', TRUE);
INSERT INTO deals (deal_id, supersedes_deal_id, customer_id, salesperson_id,
    deal_name, submitted_at, currency_code, catalog_version, policy_set_code,
    requested_delivery_date, destination_country_code, destination_region,
    shipping_service_code, terms_json, exception_justification, requirements_json,
    evidence_refs_json, salesperson_comments, deal_status, dataset_type,
    historical_decision, decision_reason, approved_by_roles_json)
VALUES ('SYN-DEAL-WORKSTATION', NULL, 'SYN-CUST-WORKSTATION', 'SYN-SALES-001',
        'Synthetic workstation quote', '2026-10-07T10:00:00Z', 'EUR', 'CATALOGUE_2026_V1',
        'BASELINE_2026', '2026-10-15', 'DE', 'DE-NW', 'standard',
        '{"payment_terms_days":30,"contract_clause_codes":["standard"],"allow_partial_delivery":false}',
        NULL, '{}', '[]', NULL, 'Submitted', 'generated_test', NULL, NULL, NULL);
INSERT INTO deal_lines (deal_line_id, deal_id, line_number, product_id, quantity,
    quoted_unit_price, configuration_json, fulfillment_group_code,
    requested_activation_date, installation_requested)
VALUES ('SYN-DL-WORKSTATION', 'SYN-DEAL-WORKSTATION', 1,
        'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 1, 1050,
        '{"selected_options":["standard"]}', NULL, NULL, FALSE);
INSERT INTO deal_runs (run_id, deal_id, original_policy_set_code,
    applied_policy_set_code, catalog_version_used, as_of_at, data_snapshot_ref,
    input_snapshot_json, config_hash, run_status, started_at, completed_at)
VALUES ('00000000-0000-4000-8000-000000240001', 'SYN-DEAL-WORKSTATION',
        'BASELINE_2026', 'BASELINE_2026', 'CATALOGUE_2026_V1',
        '2026-10-07T12:00:00Z', 'SYN-PORTFOLIO-SNAPSHOT',
        '{"fixture":"phase1c_portfolio_deal_rows"}', 'synthetic-fixture',
        'completed', '2026-10-07T12:00:00Z', '2026-10-07T12:01:00Z');
