-- Test-only runtime representations of the reviewed discount and credit thresholds.
-- Values mirror governance.profiles in calibration_config.yaml. This is not a
-- complete commercial rule compiler or production rule set.
INSERT INTO pricing_rules (pricing_rule_id,policy_set_code,rule_name,rule_type,scope_type,condition_json,action_json,priority)
VALUES
('PR-BASELINE-DIRECTOR','BASELINE_2026','Director discount threshold','volume_discount','global','{"discount_pct_gt":10}','{"flag":"director_discount"}',1),
('PR-LENIENT-DIRECTOR','LENIENT_EXPERIMENT','Director discount threshold','volume_discount','global','{"discount_pct_gt":15}','{"flag":"director_discount"}',1),
('PR-STRICT-DIRECTOR','STRICT_EXPERIMENT','Director discount threshold','volume_discount','global','{"discount_pct_gt":5}','{"flag":"director_discount"}',1);

INSERT INTO policy_rules (policy_rule_id,policy_set_code,rule_name,policy_area,scope_type,condition_json,severity,required_action,explanation_template,priority)
VALUES
('PO-BASELINE-CREDIT','BASELINE_2026','Credit exception within cap','credit','global','{"credit_over_limit_pct_gt":0,"credit_over_limit_pct_lte":15}','approval_required','escalate','Finance review required',1),
('PO-LENIENT-CREDIT','LENIENT_EXPERIMENT','Credit exception within cap','credit','global','{"credit_over_limit_pct_gt":0,"credit_over_limit_pct_lte":25}','approval_required','escalate','Finance review required',1),
('PO-STRICT-CREDIT','STRICT_EXPERIMENT','Credit exception within cap','credit','global','{"credit_over_limit_pct_gt":0,"credit_over_limit_pct_lte":5}','approval_required','escalate','Finance review required',1);

INSERT INTO approval_rules (approval_rule_id,policy_set_code,rule_name,condition_json,required_role,approval_sequence,priority)
VALUES
('AP-BASELINE-SALES','BASELINE_2026','Director discount','{"pricing_flag":"director_discount"}','Sales_Director',1,1),
('AP-LENIENT-SALES','LENIENT_EXPERIMENT','Director discount','{"pricing_flag":"director_discount"}','Sales_Director',1,1),
('AP-STRICT-SALES','STRICT_EXPERIMENT','Director discount','{"pricing_flag":"director_discount"}','Sales_Director',1,1),
('AP-BASELINE-FINANCE','BASELINE_2026','Credit exception','{"credit_exception":true}','Finance_Director',2,2),
('AP-LENIENT-FINANCE','LENIENT_EXPERIMENT','Credit exception','{"credit_exception":true}','Finance_Director',2,2),
('AP-STRICT-FINANCE','STRICT_EXPERIMENT','Credit exception','{"credit_exception":true}','Finance_Director',2,2);
