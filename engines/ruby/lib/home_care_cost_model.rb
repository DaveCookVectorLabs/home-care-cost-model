# Home Care Cost Model — Ruby reference port
#
# Reference cost model for Canadian home care service-mix decisions.
# Port of the Python reference implementation.
#
# Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
# This reference model is not clinical or financial advice.

require "csv"
require "json"

module HomeCareCostModel
  VERSION = "0.1.0"
  WEEKS_PER_MONTH = 4.345
  DISCLAIMER = "Reference model only. Not clinical or financial advice; consult a regulated health professional or registered tax practitioner for individual decisions."

  METC_FEDERAL_RATE = 0.15
  METC_FLOOR_FRAC = 0.03
  METC_ABS_FLOOR = 2759.0
  DTC_BASE = 9872.0
  CCC_CAREGIVER_BASE = 8375.0
  CCC_PHASE_START = 19666.0
  CCC_PHASE_END = 28041.0
  VIP_HOUSEKEEPING = 3072.0
  VIP_PERSONAL_CARE = 9324.0

  PROVINCIAL_FACTORS = {
    "ON" => { metc_rate: 0.0505, metc_floor: 2923, dtc_base: 10250, ccc_base: 5933 },
    "QC" => { metc_rate: 0.1400, metc_floor: 2759, dtc_base: 3494, ccc_base: 1311 },
    "BC" => { metc_rate: 0.0506, metc_floor: 2605, dtc_base: 9428, ccc_base: 5014 },
    "AB" => { metc_rate: 0.1000, metc_floor: 2824, dtc_base: 16066, ccc_base: 12307 },
    "SK" => { metc_rate: 0.1050, metc_floor: 2837, dtc_base: 10405, ccc_base: 10405 },
    "MB" => { metc_rate: 0.1080, metc_floor: 1728, dtc_base: 6180, ccc_base: 3605 },
    "NS" => { metc_rate: 0.0879, metc_floor: 1637, dtc_base: 7341, ccc_base: 4898 },
    "NB" => { metc_rate: 0.0940, metc_floor: 2344, dtc_base: 8552, ccc_base: 5197 },
    "NL" => { metc_rate: 0.0870, metc_floor: 2116, dtc_base: 7064, ccc_base: 3497 },
    "PE" => { metc_rate: 0.0980, metc_floor: 1768, dtc_base: 6890, ccc_base: 2446 },
    "YT" => { metc_rate: 0.0640, metc_floor: 2759, dtc_base: 9872, ccc_base: 8375 },
    "NT" => { metc_rate: 0.0590, metc_floor: 2759, dtc_base: 14160, ccc_base: 5167 },
    "NU" => { metc_rate: 0.0400, metc_floor: 2759, dtc_base: 15440, ccc_base: 5560 },
  }.freeze

  def self.personal_care_category_for(province)
    case province
    when "ON", "QC" then "PSW"
    when "BC", "AB", "SK", "MB" then "HCA"
    else "HSW"
    end
  end

  def self.cognitive_bump(c)
    { "intact" => 0, "mild" => 3, "moderate" => 8, "severe" => 14 }[c] || 0
  end

  def self.mobility_bump(m)
    { "independent" => 0, "cane" => 0.5, "walker" => 2, "wheelchair" => 5, "bedbound" => 12 }[m] || 0
  end

  def self.household_mod(h)
    { "alone" => 3, "with_spouse" => 1.5, "with_adult_child" => 1, "multigen" => 0.5 }[h] || 2
  end

  def self.diagnosis_nursing(d)
    { "stroke" => 4, "parkinson" => 1, "post_surgical" => 6, "chronic_mixed" => 2 }[d] || 0
  end

  def self.derive_psw_hours(adl, cognitive, mobility, informal)
    base = 7.0 * [0, 6 - adl].max + cognitive_bump(cognitive) + mobility_bump(mobility)
    credited = [informal * 0.5, base * 0.6].min
    [(base - credited), 0.0].max.round(1)
  end

  def self.derive_housekeeping_hours(iadl, household)
    base = 2.0 * [0, 8 - iadl].max + household_mod(household)
    [base, 0.0].max.round(1)
  end

  def self.derive_nursing_hours(diagnosis, cognitive)
    base = diagnosis_nursing(diagnosis)
    base += 1 if cognitive == "severe"
    [base, 0.0].max.round(1)
  end

  def self.datasets_dir
    candidates = [
      File.expand_path("../../datasets", __dir__),
      File.expand_path("../../../datasets", __dir__),
      File.expand_path("./datasets"),
    ]
    candidates.find { |d| File.exist?(File.join(d, "home_care_services_canada.csv")) }
  end

  def self.load_services
    path = File.join(datasets_dir, "home_care_services_canada.csv") rescue nil
    return {} unless path && File.exist?(path)
    result = {}
    CSV.foreach(path, headers: true) do |row|
      result["#{row["jurisdiction_code"]}|#{row["service_category"]}"] = row.to_h
    end
    result
  end

  def self.load_subsidies
    path = File.join(datasets_dir, "home_care_subsidy_programs.csv") rescue nil
    return {} unless path && File.exist?(path)
    result = {}
    CSV.foreach(path, headers: true) do |row|
      code = row["jurisdiction_code"]
      result[code] ||= row.to_h
    end
    result
  end

  def self.service_rate(services, prov, category)
    row = services["#{prov}|#{category}"]
    return 0.0 unless row
    (row["private_pay_rate_cad_median"] || "0").to_f
  end

  def self.subsidy_hours_awarded(subsidies, prov, adl)
    row = subsidies[prov]
    return 0.0 unless row
    moderate = (row["typical_psw_hours_per_week_moderate"] || "0").to_f
    high = (row["typical_psw_hours_per_week_high"] || "0").to_f
    return 0.0 if adl >= 5
    return high.round(1) if adl <= 1
    alpha = (4 - adl) / 3.0
    (moderate + alpha * (high - moderate)).round(1)
  end

  def self.calculate(input)
    input = {
      household_composition: "alone",
      cognitive_status: "intact",
      mobility_status: "independent",
      primary_diagnosis_category: "frailty",
      informal_caregiver_hours_per_week: 0.0,
      net_family_income_cad: 60000.0,
      is_veteran: false,
      has_dtc: false,
      agency_vs_private: "private",
      include_subsidy: true,
      tax_year: 2026,
    }.merge(input)

    services = load_services
    subsidies = load_subsidies

    psw_hours = derive_psw_hours(
      input[:adl_katz_score], input[:cognitive_status],
      input[:mobility_status], input[:informal_caregiver_hours_per_week]
    )
    housekeeping_hours = derive_housekeeping_hours(input[:iadl_lawton_score], input[:household_composition])
    nursing_hours = derive_nursing_hours(input[:primary_diagnosis_category], input[:cognitive_status])

    mix = if nursing_hours > 0 && psw_hours > 0
            housekeeping_hours > 0 ? "nursing+psw+housekeeping" : "nursing+psw"
          elsif psw_hours > 0 && housekeeping_hours > 0
            "psw+housekeeping"
          elsif psw_hours > 0
            "psw_only"
          elsif housekeeping_hours > 0
            "housekeeping_only"
          else
            "no_formal_services"
          end

    pc_cat = personal_care_category_for(input[:province])
    psw_rate = service_rate(services, input[:province], pc_cat)
    house_cat = input[:agency_vs_private] == "agency" ? "Cleaning_Service_Agency" : "Housekeeper_Private"
    housekeeping_rate = service_rate(services, input[:province], house_cat)
    nursing_rate = service_rate(services, input[:province], "LPN_RPN")

    private_monthly = (psw_hours * psw_rate + housekeeping_hours * housekeeping_rate + nursing_hours * nursing_rate) * WEEKS_PER_MONTH

    subsidy_hours = input[:include_subsidy] ? [subsidy_hours_awarded(subsidies, input[:province], input[:adl_katz_score]), psw_hours].min : 0.0
    subsidy_value = subsidy_hours * psw_rate * WEEKS_PER_MONTH
    oop_monthly = [private_monthly - subsidy_value, 0.0].max
    oop_annual = oop_monthly * 12.0

    pp = PROVINCIAL_FACTORS[input[:province]] || PROVINCIAL_FACTORS["ON"]
    fed_threshold = [input[:net_family_income_cad] * METC_FLOOR_FRAC, METC_ABS_FLOOR].min
    metc_fed = [(oop_annual - fed_threshold), 0.0].max * METC_FEDERAL_RATE
    prov_threshold = [input[:net_family_income_cad] * METC_FLOOR_FRAC, pp[:metc_floor]].min
    metc_prov = [(oop_annual - prov_threshold), 0.0].max * pp[:metc_rate]
    metc_credit = metc_fed + metc_prov

    dtc_credit = (input[:has_dtc] || input[:cognitive_status] == "severe") ? (DTC_BASE * METC_FEDERAL_RATE + pp[:dtc_base] * pp[:metc_rate]) : 0.0

    ccc_credit = 0.0
    if %w[with_spouse with_adult_child multigen].include?(input[:household_composition]) && psw_hours >= 10
      phase_factor = if input[:net_family_income_cad] <= CCC_PHASE_START
                       1.0
                     elsif input[:net_family_income_cad] >= CCC_PHASE_END
                       0.0
                     else
                       1.0 - (input[:net_family_income_cad] - CCC_PHASE_START) / (CCC_PHASE_END - CCC_PHASE_START)
                     end
      ccc_credit = (CCC_CAREGIVER_BASE * METC_FEDERAL_RATE + pp[:ccc_base] * pp[:metc_rate]) * phase_factor
    end

    vip_credit = input[:is_veteran] ? (VIP_HOUSEKEEPING + VIP_PERSONAL_CARE) : 0.0
    total_credits = metc_credit + dtc_credit + ccc_credit + vip_credit
    oop_after_annual = [oop_annual - total_credits, 0.0].max
    oop_after_monthly = oop_after_annual / 12.0

    total_hours = psw_hours + housekeeping_hours + nursing_hours
    all_psw_monthly = total_hours * psw_rate * WEEKS_PER_MONTH
    hybrid_savings = all_psw_monthly - private_monthly

    scope_warnings = []
    if input[:adl_katz_score] <= 4 || %w[moderate severe].include?(input[:cognitive_status])
      scope_warnings << "Personal care required: the recipient's ADL score or cognitive status indicates that personal care tasks (bathing, toileting, transfers) are needed. A housekeeper or cleaning service cannot legally substitute for a PSW/HCA in this scope. If a cleaning service is part of the plan, it must be in addition to, not instead of, personal support."
    end

    employment_warnings = []
    if input[:agency_vs_private] == "private" && (total_hours - subsidy_hours) >= 20
      employment_warnings << "At #{(total_hours - subsidy_hours).round(0)} hours per week of privately-hired care in #{input[:province]}, the CRA employer-determination test is likely to classify the family as an employer."
    end

    {
      province: input[:province],
      tax_year: input[:tax_year],
      recommended_psw_hours_per_week: psw_hours,
      recommended_housekeeping_hours_per_week: housekeeping_hours,
      recommended_nursing_hours_per_week: nursing_hours,
      recommended_service_mix: mix,
      psw_hourly_rate_cad: psw_rate.round(2),
      housekeeping_hourly_rate_cad: housekeeping_rate.round(2),
      nursing_hourly_rate_cad: nursing_rate.round(2),
      private_pay_monthly_cad: private_monthly.round(2),
      subsidy_hours_per_week_allocated: subsidy_hours.round(1),
      subsidy_value_monthly_cad: subsidy_value.round(2),
      out_of_pocket_before_credits_monthly_cad: oop_monthly.round(2),
      metc_credit_value_cad: metc_credit.round(2),
      dtc_credit_value_cad: dtc_credit.round(2),
      ccc_credit_value_cad: ccc_credit.round(2),
      vac_vip_credit_value_cad: vip_credit.round(2),
      total_credits_value_cad: total_credits.round(2),
      out_of_pocket_after_credits_monthly_cad: oop_after_monthly.round(2),
      out_of_pocket_after_credits_annual_cad: oop_after_annual.round(2),
      all_psw_cost_comparison_monthly_cad: all_psw_monthly.round(2),
      hybrid_savings_vs_all_psw_monthly_cad: hybrid_savings.round(2),
      scope_warnings: scope_warnings,
      employment_law_warnings: employment_warnings,
      currency: "CAD",
      disclaimer: DISCLAIMER,
    }
  end
end
