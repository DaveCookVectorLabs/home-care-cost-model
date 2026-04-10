// Home Care Cost Model — Rust reference port
//
// Reference cost model for Canadian home care service-mix decisions.
// Port of the Python reference implementation.
//
// Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
// This reference model is not clinical or financial advice.

use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::PathBuf;

const VERSION: &str = "0.1.0";
const WEEKS_PER_MONTH: f64 = 4.345;
const DISCLAIMER: &str = "Reference model only. Not clinical or financial advice; consult a regulated health professional or registered tax practitioner for individual decisions.";

const METC_FEDERAL_RATE: f64 = 0.15;
const METC_FLOOR_FRAC: f64 = 0.03;
const METC_ABS_FLOOR: f64 = 2759.0;
const DTC_BASE: f64 = 9872.0;
const CCC_CAREGIVER_BASE: f64 = 8375.0;
const CCC_PHASE_START: f64 = 19666.0;
const CCC_PHASE_END: f64 = 28041.0;
const VIP_HOUSEKEEPING: f64 = 3072.0;
const VIP_PERSONAL_CARE: f64 = 9324.0;

#[derive(Debug, Clone, Copy)]
struct ProvincialFactors {
    metc_rate: f64,
    metc_floor: f64,
    dtc_base: f64,
    ccc_base: f64,
}

fn provincial_factors(code: &str) -> ProvincialFactors {
    match code {
        "ON" => ProvincialFactors { metc_rate: 0.0505, metc_floor: 2923.0, dtc_base: 10250.0, ccc_base: 5933.0 },
        "QC" => ProvincialFactors { metc_rate: 0.1400, metc_floor: 2759.0, dtc_base: 3494.0, ccc_base: 1311.0 },
        "BC" => ProvincialFactors { metc_rate: 0.0506, metc_floor: 2605.0, dtc_base: 9428.0, ccc_base: 5014.0 },
        "AB" => ProvincialFactors { metc_rate: 0.1000, metc_floor: 2824.0, dtc_base: 16066.0, ccc_base: 12307.0 },
        "SK" => ProvincialFactors { metc_rate: 0.1050, metc_floor: 2837.0, dtc_base: 10405.0, ccc_base: 10405.0 },
        "MB" => ProvincialFactors { metc_rate: 0.1080, metc_floor: 1728.0, dtc_base: 6180.0, ccc_base: 3605.0 },
        "NS" => ProvincialFactors { metc_rate: 0.0879, metc_floor: 1637.0, dtc_base: 7341.0, ccc_base: 4898.0 },
        "NB" => ProvincialFactors { metc_rate: 0.0940, metc_floor: 2344.0, dtc_base: 8552.0, ccc_base: 5197.0 },
        "NL" => ProvincialFactors { metc_rate: 0.0870, metc_floor: 2116.0, dtc_base: 7064.0, ccc_base: 3497.0 },
        "PE" => ProvincialFactors { metc_rate: 0.0980, metc_floor: 1768.0, dtc_base: 6890.0, ccc_base: 2446.0 },
        "YT" => ProvincialFactors { metc_rate: 0.0640, metc_floor: 2759.0, dtc_base: 9872.0, ccc_base: 8375.0 },
        "NT" => ProvincialFactors { metc_rate: 0.0590, metc_floor: 2759.0, dtc_base: 14160.0, ccc_base: 5167.0 },
        "NU" => ProvincialFactors { metc_rate: 0.0400, metc_floor: 2759.0, dtc_base: 15440.0, ccc_base: 5560.0 },
        _ => ProvincialFactors { metc_rate: 0.0505, metc_floor: 2923.0, dtc_base: 10250.0, ccc_base: 5933.0 },
    }
}

fn personal_care_category_for(prov: &str) -> &'static str {
    match prov {
        "ON" | "QC" => "PSW",
        "BC" | "AB" | "SK" | "MB" => "HCA",
        _ => "HSW",
    }
}

fn cognitive_bump(c: &str) -> f64 {
    match c {
        "intact" => 0.0,
        "mild" => 3.0,
        "moderate" => 8.0,
        "severe" => 14.0,
        _ => 0.0,
    }
}

fn mobility_bump(m: &str) -> f64 {
    match m {
        "independent" => 0.0,
        "cane" => 0.5,
        "walker" => 2.0,
        "wheelchair" => 5.0,
        "bedbound" => 12.0,
        _ => 0.0,
    }
}

fn household_mod(h: &str) -> f64 {
    match h {
        "alone" => 3.0,
        "with_spouse" => 1.5,
        "with_adult_child" => 1.0,
        "multigen" => 0.5,
        _ => 2.0,
    }
}

fn diagnosis_nursing(d: &str) -> f64 {
    match d {
        "stroke" => 4.0,
        "parkinson" => 1.0,
        "post_surgical" => 6.0,
        "chronic_mixed" => 2.0,
        _ => 0.0,
    }
}

fn derive_psw_hours(adl: i32, cognitive: &str, mobility: &str, informal: f64) -> f64 {
    let base = 7.0 * (6 - adl).max(0) as f64 + cognitive_bump(cognitive) + mobility_bump(mobility);
    let credited = (informal * 0.5).min(base * 0.6);
    round1((base - credited).max(0.0))
}

fn derive_housekeeping_hours(iadl: i32, household: &str) -> f64 {
    let base = 2.0 * (8 - iadl).max(0) as f64 + household_mod(household);
    round1(base.max(0.0))
}

fn derive_nursing_hours(diagnosis: &str, cognitive: &str) -> f64 {
    let mut base = diagnosis_nursing(diagnosis);
    if cognitive == "severe" { base += 1.0; }
    round1(base.max(0.0))
}

fn round1(v: f64) -> f64 { (v * 10.0).round() / 10.0 }
fn round2(v: f64) -> f64 { (v * 100.0).round() / 100.0 }

// CSV loader — minimal stdlib-only implementation
fn load_csv(path: &PathBuf) -> Vec<HashMap<String, String>> {
    let content = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(_) => return vec![],
    };
    let mut lines = content.lines();
    let header_line = match lines.next() {
        Some(l) => l,
        None => return vec![],
    };
    let headers: Vec<&str> = header_line.split(',').collect();
    let mut rows = vec![];
    for line in lines {
        // Naive CSV parser (no quote handling); our CSVs do include quoted fields
        let fields = parse_csv_line(line);
        let mut row = HashMap::new();
        for (i, h) in headers.iter().enumerate() {
            row.insert(h.to_string(), fields.get(i).cloned().unwrap_or_default());
        }
        rows.push(row);
    }
    rows
}

fn parse_csv_line(line: &str) -> Vec<String> {
    let mut fields = vec![];
    let mut current = String::new();
    let mut in_quotes = false;
    for c in line.chars() {
        if c == '"' {
            in_quotes = !in_quotes;
        } else if c == ',' && !in_quotes {
            fields.push(current.clone());
            current.clear();
        } else {
            current.push(c);
        }
    }
    fields.push(current);
    fields
}

fn find_datasets_dir() -> Option<PathBuf> {
    let candidates = vec![
        PathBuf::from("./datasets"),
        PathBuf::from("../../datasets"),
    ];
    for c in candidates {
        if c.join("home_care_services_canada.csv").exists() {
            return Some(c);
        }
    }
    None
}

fn service_rate(services: &[HashMap<String, String>], prov: &str, category: &str) -> f64 {
    for row in services {
        if row.get("jurisdiction_code").map(|s| s.as_str()) == Some(prov)
            && row.get("service_category").map(|s| s.as_str()) == Some(category) {
            if let Some(rate_str) = row.get("private_pay_rate_cad_median") {
                if let Ok(v) = rate_str.parse::<f64>() { return v; }
            }
        }
    }
    0.0
}

fn subsidy_hours_awarded(subsidies: &[HashMap<String, String>], prov: &str, adl: i32) -> f64 {
    for row in subsidies {
        if row.get("jurisdiction_code").map(|s| s.as_str()) == Some(prov) {
            let moderate: f64 = row.get("typical_psw_hours_per_week_moderate")
                .and_then(|s| s.parse().ok()).unwrap_or(0.0);
            let high: f64 = row.get("typical_psw_hours_per_week_high")
                .and_then(|s| s.parse().ok()).unwrap_or(0.0);
            if adl >= 5 { return 0.0; }
            if adl <= 1 { return round1(high); }
            let alpha = (4 - adl) as f64 / 3.0;
            return round1(moderate + alpha * (high - moderate));
        }
    }
    0.0
}

#[derive(Debug)]
struct CalculateInput {
    adl: i32,
    iadl: i32,
    province: String,
    household: String,
    cognitive: String,
    mobility: String,
    diagnosis: String,
    informal: f64,
    net_income: f64,
    is_veteran: bool,
    has_dtc: bool,
    agency_vs_private: String,
    include_subsidy: bool,
    tax_year: i32,
}

#[derive(Debug)]
struct CalculateResult {
    province: String,
    tax_year: i32,
    psw_hours: f64,
    housekeeping_hours: f64,
    nursing_hours: f64,
    service_mix: String,
    psw_rate: f64,
    housekeeping_rate: f64,
    nursing_rate: f64,
    private_monthly: f64,
    subsidy_hours: f64,
    subsidy_value: f64,
    oop_before_monthly: f64,
    metc_credit: f64,
    dtc_credit: f64,
    ccc_credit: f64,
    vip_credit: f64,
    total_credits: f64,
    oop_after_monthly: f64,
    oop_after_annual: f64,
    all_psw_monthly: f64,
    hybrid_savings: f64,
    scope_warnings: Vec<String>,
    employment_warnings: Vec<String>,
}

fn calculate(
    input: &CalculateInput,
    services: &[HashMap<String, String>],
    subsidies: &[HashMap<String, String>],
) -> CalculateResult {
    let psw_hours = derive_psw_hours(input.adl, &input.cognitive, &input.mobility, input.informal);
    let housekeeping_hours = derive_housekeeping_hours(input.iadl, &input.household);
    let nursing_hours = derive_nursing_hours(&input.diagnosis, &input.cognitive);

    let mix = if nursing_hours > 0.0 && psw_hours > 0.0 {
        if housekeeping_hours > 0.0 { "nursing+psw+housekeeping" } else { "nursing+psw" }
    } else if psw_hours > 0.0 && housekeeping_hours > 0.0 {
        "psw+housekeeping"
    } else if psw_hours > 0.0 {
        "psw_only"
    } else if housekeeping_hours > 0.0 {
        "housekeeping_only"
    } else {
        "no_formal_services"
    };

    let pc_cat = personal_care_category_for(&input.province);
    let psw_rate = service_rate(services, &input.province, pc_cat);
    let house_cat = if input.agency_vs_private == "agency" { "Cleaning_Service_Agency" } else { "Housekeeper_Private" };
    let housekeeping_rate = service_rate(services, &input.province, house_cat);
    let nursing_rate = service_rate(services, &input.province, "LPN_RPN");

    let private_monthly = (psw_hours * psw_rate + housekeeping_hours * housekeeping_rate + nursing_hours * nursing_rate) * WEEKS_PER_MONTH;

    let subsidy_hours = if input.include_subsidy {
        subsidy_hours_awarded(subsidies, &input.province, input.adl).min(psw_hours)
    } else { 0.0 };
    let subsidy_value = subsidy_hours * psw_rate * WEEKS_PER_MONTH;
    let oop_monthly = (private_monthly - subsidy_value).max(0.0);
    let oop_annual = oop_monthly * 12.0;

    let pp = provincial_factors(&input.province);
    let fed_threshold = (input.net_income * METC_FLOOR_FRAC).min(METC_ABS_FLOOR);
    let metc_fed = ((oop_annual - fed_threshold).max(0.0)) * METC_FEDERAL_RATE;
    let prov_threshold = (input.net_income * METC_FLOOR_FRAC).min(pp.metc_floor);
    let metc_prov = ((oop_annual - prov_threshold).max(0.0)) * pp.metc_rate;
    let metc_credit = metc_fed + metc_prov;

    let dtc_credit = if input.has_dtc || input.cognitive == "severe" {
        DTC_BASE * METC_FEDERAL_RATE + pp.dtc_base * pp.metc_rate
    } else { 0.0 };

    let ccc_credit = {
        let eligible_household = matches!(input.household.as_str(), "with_spouse" | "with_adult_child" | "multigen");
        if eligible_household && psw_hours >= 10.0 {
            let phase_factor = if input.net_income <= CCC_PHASE_START { 1.0 }
                else if input.net_income >= CCC_PHASE_END { 0.0 }
                else { 1.0 - (input.net_income - CCC_PHASE_START) / (CCC_PHASE_END - CCC_PHASE_START) };
            (CCC_CAREGIVER_BASE * METC_FEDERAL_RATE + pp.ccc_base * pp.metc_rate) * phase_factor
        } else { 0.0 }
    };

    let vip_credit = if input.is_veteran { VIP_HOUSEKEEPING + VIP_PERSONAL_CARE } else { 0.0 };
    let total_credits = metc_credit + dtc_credit + ccc_credit + vip_credit;
    let oop_after_annual = (oop_annual - total_credits).max(0.0);
    let oop_after_monthly = oop_after_annual / 12.0;

    let total_hours = psw_hours + housekeeping_hours + nursing_hours;
    let all_psw_monthly = total_hours * psw_rate * WEEKS_PER_MONTH;
    let hybrid_savings = all_psw_monthly - private_monthly;

    let mut scope_warnings: Vec<String> = vec![];
    if input.adl <= 4 || matches!(input.cognitive.as_str(), "moderate" | "severe") {
        scope_warnings.push("Personal care required: the recipient's ADL score or cognitive status indicates that personal care tasks (bathing, toileting, transfers) are needed. A housekeeper or cleaning service cannot legally substitute for a PSW/HCA in this scope. If a cleaning service is part of the plan, it must be in addition to, not instead of, personal support.".to_string());
    }

    let mut employment_warnings: Vec<String> = vec![];
    if input.agency_vs_private == "private" && (total_hours - subsidy_hours) >= 20.0 {
        employment_warnings.push(format!(
            "At {:.0} hours per week of privately-hired care in {}, the CRA employer-determination test is likely to classify the family as an employer.",
            total_hours - subsidy_hours, input.province
        ));
    }

    CalculateResult {
        province: input.province.clone(),
        tax_year: input.tax_year,
        psw_hours, housekeeping_hours, nursing_hours,
        service_mix: mix.to_string(),
        psw_rate: round2(psw_rate),
        housekeeping_rate: round2(housekeeping_rate),
        nursing_rate: round2(nursing_rate),
        private_monthly: round2(private_monthly),
        subsidy_hours: round1(subsidy_hours),
        subsidy_value: round2(subsidy_value),
        oop_before_monthly: round2(oop_monthly),
        metc_credit: round2(metc_credit),
        dtc_credit: round2(dtc_credit),
        ccc_credit: round2(ccc_credit),
        vip_credit: round2(vip_credit),
        total_credits: round2(total_credits),
        oop_after_monthly: round2(oop_after_monthly),
        oop_after_annual: round2(oop_after_annual),
        all_psw_monthly: round2(all_psw_monthly),
        hybrid_savings: round2(hybrid_savings),
        scope_warnings,
        employment_warnings,
    }
}

fn main() {
    let datasets = find_datasets_dir().unwrap_or_else(|| PathBuf::from("./datasets"));
    let services = load_csv(&datasets.join("home_care_services_canada.csv"));
    let subsidies = load_csv(&datasets.join("home_care_subsidy_programs.csv"));

    let args: Vec<String> = env::args().collect();
    if args.iter().any(|a| a == "--health") {
        println!("{{\"status\":\"ok\",\"engine\":\"rust\",\"version\":\"{}\",\"services_loaded\":{},\"subsidies_loaded\":{},\"disclaimer\":\"{}\"}}",
            VERSION, services.len(), subsidies.len(), DISCLAIMER);
        return;
    }

    // Sample: Mr. B, Vancouver BC, moderate dementia
    let input = CalculateInput {
        adl: 2, iadl: 1,
        province: "BC".to_string(),
        household: "with_spouse".to_string(),
        cognitive: "moderate".to_string(),
        mobility: "walker".to_string(),
        diagnosis: "dementia".to_string(),
        informal: 20.0,
        net_income: 72000.0,
        is_veteran: false,
        has_dtc: true,
        agency_vs_private: "private".to_string(),
        include_subsidy: true,
        tax_year: 2026,
    };
    let result = calculate(&input, &services, &subsidies);
    println!("Home Care Cost Model — Rust Engine v{}", VERSION);
    println!("======================================================");
    println!("Jurisdiction: {}   Tax year: {}", result.province, result.tax_year);
    println!("Recommended PSW hours/week:      {}", result.psw_hours);
    println!("Recommended housekeeping h/w:    {}", result.housekeeping_hours);
    println!("Recommended nursing h/w:         {}", result.nursing_hours);
    println!("Service mix:                     {}", result.service_mix);
    println!("Private pay monthly CAD:         ${:.2}", result.private_monthly);
    println!("Subsidy value monthly CAD:       ${:.2}", result.subsidy_value);
    println!("OoP before credits monthly CAD:  ${:.2}", result.oop_before_monthly);
    println!("Tax credits annual CAD:          ${:.2}", result.total_credits);
    println!("OoP after credits monthly CAD:   ${:.2}", result.oop_after_monthly);
    println!("OoP after credits annual CAD:    ${:.2}", result.oop_after_annual);
    println!("All-PSW comparison monthly CAD:  ${:.2}", result.all_psw_monthly);
    println!("Hybrid savings monthly CAD:      ${:.2}", result.hybrid_savings);
    if !result.scope_warnings.is_empty() {
        println!();
        println!("Scope warnings:");
        for w in &result.scope_warnings { println!("  ! {}", w); }
    }
    println!();
    println!("Disclaimer: {}", DISCLAIMER);
}
