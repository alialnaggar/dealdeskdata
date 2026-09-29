-- Phase 1C PostgreSQL smoke test. Execute only after schema.sql in a disposable
-- PostgreSQL 15+ database: psql -X -v ON_ERROR_STOP=1 -f phase1c_schema_smoke.sql
-- All test rows and helper functions are rolled back. This file has not yet
-- been executed in PostgreSQL in the current workspace.
\set ON_ERROR_STOP on
BEGIN;
SET search_path TO deal_desk, public;

CREATE FUNCTION assert_true(p_condition BOOLEAN, p_message TEXT) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF p_condition IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'assertion failed: %', p_message;
    END IF;
END $$;

CREATE FUNCTION assert_rejected(p_statement TEXT, p_expected_fragment TEXT) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE failure TEXT;
BEGIN
    BEGIN
        EXECUTE p_statement;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS failure = MESSAGE_TEXT;
    END;
    IF failure IS NULL THEN
        RAISE EXCEPTION 'expected rejection, but SQL was accepted: %', p_statement;
    END IF;
    IF position(p_expected_fragment IN failure) = 0 THEN
        RAISE EXCEPTION 'unexpected rejection: expected %, got %', p_expected_fragment, failure;
    END IF;
END $$;

-- Catalogue, one customer and one supplier.
INSERT INTO products
 (product_id,product_code,catalog_version,product_name,category,product_type,
  list_price,standard_cost,billing_model,unit_of_measure,is_sellable,
  fulfillment_mode,stock_uom)
VALUES
 ('P-STOCK','STOCK-SERVER','CATALOGUE_2026_V1','Synthetic stocked server','servers','physical',
  1000,700,'one_time','device',TRUE,'stocked_finished','each'),
 ('P-MTO','BUILD-SERVER','CATALOGUE_2026_V1','Synthetic built server','servers','physical',
  2000,1200,'one_time','device',TRUE,'make_to_order','each'),
 ('P-COMP','COMP-MOD','CATALOGUE_2026_V1','Synthetic component','components','component',
  0,100,'not_applicable','component_unit',FALSE,'component','component_unit'),
 ('P-DIG','USER-LIC','CATALOGUE_2026_V1','Synthetic yearly licence','software','software',
  120,40,'recurring','user_year',TRUE,'digital_activation','not_applicable'),
 ('P-OTHER-VERSION','OTHER-VERSION','CATALOGUE_2026_V2','Wrong catalogue version','servers','physical',
  1000,700,'one_time','device',TRUE,'stocked_finished','each');
INSERT INTO customers
 (customer_id,customer_code,customer_name,size_segment,industry,country_code,region,customer_since,account_status)
VALUES ('C-1','C-001','Synthetic customer','SMB','technology','DE','Berlin','2024-01-01','Active');
INSERT INTO customer_credit_profiles
 (customer_id,credit_limit,unbilled_committed_amount,commitments_as_of_at,
  commitment_evidence_ref,risk_rating,credit_status,default_payment_terms_days,last_review_date)
VALUES ('C-1',100000,20000,'2026-09-29 06:00+00','COMMIT-SNAP-1','Low','Active',30,'2026-09-20');
INSERT INTO accounts_receivable
 (receivable_id,customer_id,invoice_number,invoice_date,due_date,
  original_amount,outstanding_amount,status,as_of_date)
VALUES ('AR-1','C-1','INV-001','2026-08-01','2026-10-01',30000,30000,'Open','2026-09-29');
INSERT INTO suppliers (supplier_id,supplier_code,supplier_name,country_code,status)
VALUES ('S-1','SUP-001','Synthetic supplier','DE','active');

-- Physical stock, recipe, capacity and a binding receipt.
INSERT INTO inventory
 (inventory_id,product_id,location_id,quantity_on_hand,quantity_allocated,snapshot_at)
VALUES
 ('ST-1','P-STOCK','WH-EU-CENTRAL',20,12,'2026-09-29 06:00+00'),
 ('ST-COMP','P-COMP','WH-EU-CENTRAL',9,0,'2026-09-29 06:00+00');
INSERT INTO bom_headers
 (bom_id,finished_product_id,catalog_version,bom_version,
  configuration_signature_json,output_quantity,effective_from,status)
VALUES ('BOM-1','P-MTO','CATALOGUE_2026_V1','V1','{}',1,'2026-09-01 00:00+00','active');
INSERT INTO bom_lines
 (bom_line_id,bom_id,component_product_id,required_quantity_per_output,priority)
VALUES ('BL-1','BOM-1','P-COMP',2,1);
INSERT INTO production_requirements
 (requirement_id,bom_id,operation_seq,capability_code,resource_type,
  setup_hours,hours_per_unit,batch_size,status)
VALUES ('REQ-1','BOM-1',1,'assembly','workforce',1,.5,10,'active');
INSERT INTO production_capacity
 (capacity_id,location_id,capability_code,resource_type,capacity_date,time_zone,
  available_capacity_hours,allocated_capacity_hours,snapshot_at,status,evidence_ref)
VALUES ('CAP-1','WH-EU-CENTRAL','assembly','workforce','2026-09-30','Europe/Berlin',
        16,8,'2026-09-29 06:00+00','active','CAP-SNAP-1');
INSERT INTO purchase_orders
 (purchase_order_id,supplier_id,reference_number,ordered_at,confirmed_at,status,destination_location_id)
VALUES ('PO-1','S-1','PO-001','2026-09-27 09:00+00','2026-09-28 09:00+00','Confirmed','WH-EU-CENTRAL');
INSERT INTO inbound_supply
 (supply_id,purchase_order_id,product_id,location_id,quantity,quantity_allocated,
  expected_date,confirmed_at,status,reference_number,evidence_ref,valid_until)
VALUES ('IN-1','PO-1','P-STOCK','WH-EU-CENTRAL',5,2,'2026-09-30',
        '2026-09-28 10:00+00','Confirmed','IN-001','CONF-001','2026-10-05 00:00+00');
INSERT INTO shipping_lanes
 (lane_id,origin_location_id,origin_time_zone,destination_country_code,
  destination_region,shipping_service_code,transit_workdays,dispatch_weekdays_json,cutoff_local_time)
VALUES ('LANE-1','WH-EU-CENTRAL','Europe/Berlin','DE','Berlin','standard',2,'[1,2,3,4,5]','15:00');

-- Digital commitment is an entitlement pool, not warehouse inventory.
INSERT INTO digital_capacity
 (digital_capacity_id,product_id,configuration_signature_json,region_code,term_code,
  capacity_unit,capacity_total,quantity_allocated,activation_lead_days,commitment_status,
  confirmed_at,valid_until,snapshot_at,evidence_ref)
VALUES ('DC-1','P-DIG','{}','DE','12m','user',10,4,2,'binding',
        '2026-09-28 10:00+00','2026-10-05 00:00+00','2026-09-29 06:00+00','BIND-001');

-- Draft header, then lines, then immutable submission.
INSERT INTO deals
 (deal_id,customer_id,salesperson_id,deal_name,submitted_at,currency_code,
  catalog_version,policy_set_code,requested_delivery_date,destination_country_code,
  destination_region,shipping_service_code,terms_json,deal_status,dataset_type)
VALUES
 ('D-PHYS','C-1','SALES-1','Stocked server quote','2026-09-29 07:00+00','EUR',
  'CATALOGUE_2026_V1','BASELINE_2026','2026-10-05','DE','Berlin','standard',
  '{"payment_terms_days":30,"contract_clause_codes":["standard"],"allow_partial_delivery":true}',
  'Draft','generated_test'),
 ('D-DIG','C-1','SALES-1','Licence quote','2026-09-29 07:00+00','EUR',
  'CATALOGUE_2026_V1','BASELINE_2026',NULL,NULL,NULL,NULL,
  '{"payment_terms_days":30,"contract_months":12,"contract_clause_codes":["standard"],"allow_partial_delivery":false}',
  'Draft','generated_test');
INSERT INTO deal_lines
 (deal_line_id,deal_id,line_number,product_id,quantity,quoted_unit_price,
  configuration_json,requested_activation_date)
VALUES
 ('DL-PHYS','D-PHYS',1,'P-STOCK',10,900,'{}',NULL),
 ('DL-DIG','D-DIG',1,'P-DIG',5,100,'{"units_per_period":5}','2026-10-01');
UPDATE deals SET deal_status='Submitted' WHERE deal_id IN ('D-PHYS','D-DIG');
SET CONSTRAINTS ALL IMMEDIATE;
INSERT INTO deal_runs
 (run_id,deal_id,original_policy_set_code,applied_policy_set_code,catalog_version_used,
  as_of_at,data_snapshot_ref,input_snapshot_json,config_hash,run_status,started_at,completed_at)
VALUES
 ('00000000-0000-4000-8000-000000000001','D-PHYS','BASELINE_2026','BASELINE_2026',
  'CATALOGUE_2026_V1','2026-09-29 07:30+00','SNAP-1','{}','HASH-1','completed',
  '2026-09-29 08:00+00','2026-09-29 08:02+00');
INSERT INTO agent_execution_log
 (run_id,deal_id,agent_name,attempt_number,started_at,completed_at,status,
  input_snapshot_json,output_json,applied_policy_set_code,catalog_version_used)
VALUES
 ('00000000-0000-4000-8000-000000000001','D-PHYS','Configuration',1,
  '2026-09-29 08:00+00','2026-09-29 08:01+00','Success','{}','{}',
  'BASELINE_2026','CATALOGUE_2026_V1');

-- Independent expected arithmetic; this does not assert shipping arrival.
SELECT assert_true(
 (SELECT quantity_on_hand-quantity_allocated FROM inventory WHERE inventory_id='ST-1')=8,
 '8 physical units free now');
SELECT assert_true(
 (SELECT quantity-quantity_allocated FROM inbound_supply WHERE supply_id='IN-1')=3,
 '3 incoming units not already allocated');
SELECT assert_true(
 (SELECT capacity_total-quantity_allocated FROM digital_capacity WHERE digital_capacity_id='DC-1')=6,
 '6 concurrent digital units free');
SELECT assert_true(
 (SELECT quantity FROM deal_lines WHERE deal_line_id='DL-DIG')=5,
 '12-month yearly licence requires 5 simultaneous units');
SELECT assert_true(
 (SELECT available_capacity_hours-allocated_capacity_hours FROM production_capacity WHERE capacity_id='CAP-1')=8,
 '8 workforce hours free on selected day');
SELECT assert_true(
 (SELECT required_quantity_per_output*8 FROM bom_lines WHERE bom_line_id='BL-1')=16,
 'eight newly built units need 16 component units');
SELECT assert_true(
 (SELECT ceil(8::numeric/batch_size)*setup_hours + 8*hours_per_unit
    FROM production_requirements WHERE requirement_id='REQ-1')=5,
 'eight newly built units need five workforce hours');
SELECT assert_true(
 (SELECT (p.list_price-l.quoted_unit_price)/p.list_price*100
    FROM deal_lines l JOIN products p USING (product_id) WHERE l.deal_line_id='DL-PHYS')=10,
 'quoted stocked line has a derived 10 percent discount');
SELECT assert_true(
 (SELECT unbilled_committed_amount FROM customer_credit_profiles WHERE customer_id='C-1')
 + (SELECT sum(outstanding_amount) FROM accounts_receivable WHERE customer_id='C-1')
 + (SELECT sum(quantity*quoted_unit_price) FROM deal_lines WHERE deal_id='D-PHYS')=59000,
 'post-deal exposure combines unbilled commitments, AR and this quote exactly once');

-- Invalid inserts/edits must fail with the intended guard, not a random error.
SELECT assert_rejected(
 $bad$INSERT INTO inventory VALUES ('BAD-DIG-STOCK','P-DIG','WH-EU-CENTRAL',1,0,'2026-09-29 06:00+00')$bad$,
 'physical supply table inventory cannot reference product mode digital_activation');
SELECT assert_rejected(
 $bad$INSERT INTO shipping_lanes
 (lane_id,origin_location_id,origin_time_zone,destination_country_code,destination_region,
  shipping_service_code,transit_workdays,dispatch_weekdays_json,cutoff_local_time)
 VALUES ('BAD-ZONE','WH-EU-CENTRAL','Fake/Time','DE','Berlin','express',1,'[1,2,3,4,5]','15:00')$bad$,
 'unknown IANA time zone');
SELECT assert_rejected(
 $bad$INSERT INTO bom_headers
 (bom_id,finished_product_id,catalog_version,bom_version,configuration_signature_json,
  output_quantity,effective_from,status)
 VALUES ('BOM-OVERLAP','P-MTO','CATALOGUE_2026_V1','V2','{}',1,'2026-09-15 00:00+00','active')$bad$,
 'overlapping effective BOM');
SELECT assert_rejected(
 $bad$UPDATE purchase_orders SET status='Cancelled' WHERE purchase_order_id='PO-1'$bad$,
 'still has active confirmed receipt');
SELECT assert_rejected(
 $bad$UPDATE deals SET deal_name='Altered quote' WHERE deal_id='D-PHYS'$bad$,
 'inputs are immutable');

-- Another draft is useful for checking wrong-version lines and missing terms.
INSERT INTO deals
 (deal_id,customer_id,salesperson_id,deal_name,submitted_at,currency_code,catalog_version,
  policy_set_code,terms_json,deal_status,dataset_type)
VALUES ('D-BAD','C-1','SALES-1','Incomplete quote','2026-09-29 07:00+00','EUR',
        'CATALOGUE_2026_V1','BASELINE_2026',
        '{"payment_terms_days":30,"contract_clause_codes":["standard"]}',
        'Draft','generated_test');
SELECT assert_rejected(
 $bad$INSERT INTO deal_lines
 (deal_line_id,deal_id,line_number,product_id,quantity,quoted_unit_price)
 VALUES ('BAD-VERSION','D-BAD',1,'P-OTHER-VERSION',1,900)$bad$,
 'wrong-version product');
SELECT assert_rejected(
 $bad$UPDATE deals SET deal_status='Submitted' WHERE deal_id='D-BAD'$bad$,
 'requires boolean allow_partial_delivery');

INSERT INTO deals
 (deal_id,customer_id,salesperson_id,deal_name,submitted_at,currency_code,catalog_version,
  policy_set_code,terms_json,deal_status,dataset_type)
VALUES ('D-BAD-TERM','C-1','SALES-1','Wrong recurring quantity','2026-09-29 07:00+00','EUR',
        'CATALOGUE_2026_V1','BASELINE_2026',
        '{"payment_terms_days":30,"contract_months":12,"contract_clause_codes":["standard"],"allow_partial_delivery":false}',
        'Draft','generated_test');
INSERT INTO deal_lines
 (deal_line_id,deal_id,line_number,product_id,quantity,quoted_unit_price,configuration_json)
VALUES ('BAD-TERM','D-BAD-TERM',1,'P-DIG',60,100,'{"units_per_period":5}');
SELECT assert_rejected(
 $bad$UPDATE deals SET deal_status='Submitted' WHERE deal_id='D-BAD-TERM'$bad$,
 'quantity mismatches full-term units');

SELECT 'PASS: connected rows, nine arithmetic checks and eight targeted rejections' AS smoke_result;
ROLLBACK;
