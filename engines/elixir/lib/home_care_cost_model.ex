defmodule HomeCareCostModel do
  @moduledoc """
  Home Care Cost Model — Elixir reference port.

  Reference cost model for Canadian home care service-mix decisions.
  Port of the Python reference implementation.

  Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
  This reference model is not clinical or financial advice.
  """

  @version "0.1.0"
  @weeks_per_month 4.345
  @disclaimer "Reference model only. Not clinical or financial advice; consult a regulated health professional or registered tax practitioner for individual decisions."

  @metc_federal_rate 0.15
  @metc_floor_frac 0.03
  @metc_abs_floor 2759.0
  @dtc_base 9872.0
  @ccc_caregiver_base 8375.0
  @ccc_phase_start 19666.0
  @ccc_phase_end 28041.0
  @vip_housekeeping 3072.0
  @vip_personal_care 9324.0

  @provincial_factors %{
    "ON" => %{metc_rate: 0.0505, metc_floor: 2923, dtc_base: 10250, ccc_base: 5933},
    "QC" => %{metc_rate: 0.1400, metc_floor: 2759, dtc_base: 3494, ccc_base: 1311},
    "BC" => %{metc_rate: 0.0506, metc_floor: 2605, dtc_base: 9428, ccc_base: 5014},
    "AB" => %{metc_rate: 0.1000, metc_floor: 2824, dtc_base: 16066, ccc_base: 12307},
    "SK" => %{metc_rate: 0.1050, metc_floor: 2837, dtc_base: 10405, ccc_base: 10405},
    "MB" => %{metc_rate: 0.1080, metc_floor: 1728, dtc_base: 6180, ccc_base: 3605},
    "NS" => %{metc_rate: 0.0879, metc_floor: 1637, dtc_base: 7341, ccc_base: 4898},
    "NB" => %{metc_rate: 0.0940, metc_floor: 2344, dtc_base: 8552, ccc_base: 5197},
    "NL" => %{metc_rate: 0.0870, metc_floor: 2116, dtc_base: 7064, ccc_base: 3497},
    "PE" => %{metc_rate: 0.0980, metc_floor: 1768, dtc_base: 6890, ccc_base: 2446},
    "YT" => %{metc_rate: 0.0640, metc_floor: 2759, dtc_base: 9872, ccc_base: 8375},
    "NT" => %{metc_rate: 0.0590, metc_floor: 2759, dtc_base: 14160, ccc_base: 5167},
    "NU" => %{metc_rate: 0.0400, metc_floor: 2759, dtc_base: 15440, ccc_base: 5560}
  }

  def version, do: @version
  def disclaimer, do: @disclaimer

  defp personal_care_category_for(prov) when prov in ["ON", "QC"], do: "PSW"
  defp personal_care_category_for(prov) when prov in ["BC", "AB", "SK", "MB"], do: "HCA"
  defp personal_care_category_for(_), do: "HSW"

  defp cognitive_bump("intact"), do: 0.0
  defp cognitive_bump("mild"), do: 3.0
  defp cognitive_bump("moderate"), do: 8.0
  defp cognitive_bump("severe"), do: 14.0
  defp cognitive_bump(_), do: 0.0

  defp mobility_bump("independent"), do: 0.0
  defp mobility_bump("cane"), do: 0.5
  defp mobility_bump("walker"), do: 2.0
  defp mobility_bump("wheelchair"), do: 5.0
  defp mobility_bump("bedbound"), do: 12.0
  defp mobility_bump(_), do: 0.0

  defp household_mod("alone"), do: 3.0
  defp household_mod("with_spouse"), do: 1.5
  defp household_mod("with_adult_child"), do: 1.0
  defp household_mod("multigen"), do: 0.5
  defp household_mod(_), do: 2.0

  defp diagnosis_nursing("stroke"), do: 4.0
  defp diagnosis_nursing("parkinson"), do: 1.0
  defp diagnosis_nursing("post_surgical"), do: 6.0
  defp diagnosis_nursing("chronic_mixed"), do: 2.0
  defp diagnosis_nursing(_), do: 0.0

  def derive_psw_hours(adl, cognitive, mobility, informal) do
    base = 7.0 * max(0, 6 - adl) + cognitive_bump(cognitive) + mobility_bump(mobility)
    credited = min(informal * 0.5, base * 0.6)
    Float.round(max(0.0, base - credited), 1)
  end

  def derive_housekeeping_hours(iadl, household) do
    base = 2.0 * max(0, 8 - iadl) + household_mod(household)
    Float.round(max(0.0, base), 1)
  end

  def derive_nursing_hours(diagnosis, cognitive) do
    base = diagnosis_nursing(diagnosis)
    base = if cognitive == "severe", do: base + 1.0, else: base
    Float.round(max(0.0, base), 1)
  end

  defp round2(v), do: Float.round(v * 1.0, 2)
  defp round1(v), do: Float.round(v * 1.0, 1)

  defp datasets_dir do
    candidates = [
      Path.expand("../../datasets", __DIR__),
      Path.expand("../../../datasets", __DIR__),
      "./datasets"
    ]
    Enum.find(candidates, &File.exists?(Path.join(&1, "home_care_services_canada.csv")))
  end

  defp parse_csv_line(line) do
    parse_csv_line(line, "", [], false)
  end

  defp parse_csv_line("", acc, fields, _in_q), do: Enum.reverse([acc | fields])

  defp parse_csv_line(<<?", rest::binary>>, acc, fields, in_q) do
    parse_csv_line(rest, acc, fields, not in_q)
  end

  defp parse_csv_line(<<?,, rest::binary>>, acc, fields, false) do
    parse_csv_line(rest, "", [acc | fields], false)
  end

  defp parse_csv_line(<<ch::utf8, rest::binary>>, acc, fields, in_q) do
    parse_csv_line(rest, acc <> <<ch::utf8>>, fields, in_q)
  end

  defp load_csv(path) do
    case File.read(path) do
      {:ok, content} ->
        lines = String.split(String.trim(content), "\n")
        [header_line | data_lines] = lines
        headers = parse_csv_line(header_line)
        Enum.map(data_lines, fn line ->
          fields = parse_csv_line(line)
          Enum.zip(headers, fields) |> Map.new()
        end)
      _ -> []
    end
  end

  def load_services do
    case datasets_dir() do
      nil -> %{}
      dir ->
        dir
        |> Path.join("home_care_services_canada.csv")
        |> load_csv()
        |> Enum.reduce(%{}, fn row, acc ->
          key = "#{row["jurisdiction_code"]}|#{row["service_category"]}"
          Map.put_new(acc, key, row)
        end)
    end
  end

  def load_subsidies do
    case datasets_dir() do
      nil -> %{}
      dir ->
        dir
        |> Path.join("home_care_subsidy_programs.csv")
        |> load_csv()
        |> Enum.reduce(%{}, fn row, acc ->
          Map.put_new(acc, row["jurisdiction_code"], row)
        end)
    end
  end

  defp parse_float(s) when is_binary(s) do
    case Float.parse(s) do
      {f, _} -> f
      :error -> 0.0
    end
  end
  defp parse_float(_), do: 0.0

  defp service_rate(services, prov, category) do
    row = Map.get(services, "#{prov}|#{category}")
    if row, do: parse_float(row["private_pay_rate_cad_median"]), else: 0.0
  end

  defp subsidy_hours_awarded(subsidies, prov, adl) do
    row = Map.get(subsidies, prov)
    if row do
      moderate = parse_float(row["typical_psw_hours_per_week_moderate"])
      high = parse_float(row["typical_psw_hours_per_week_high"])
      cond do
        adl >= 5 -> 0.0
        adl <= 1 -> round1(high)
        true ->
          alpha = (4 - adl) / 3.0
          round1(moderate + alpha * (high - moderate))
      end
    else
      0.0
    end
  end

  def calculate(input) do
    input = Map.merge(%{
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
      tax_year: 2026
    }, input)

    services = load_services()
    subsidies = load_subsidies()

    psw = derive_psw_hours(
      input[:adl_katz_score], input[:cognitive_status],
      input[:mobility_status], input[:informal_caregiver_hours_per_week] * 1.0
    )
    housekeeping = derive_housekeeping_hours(input[:iadl_lawton_score], input[:household_composition])
    nursing = derive_nursing_hours(input[:primary_diagnosis_category], input[:cognitive_status])

    mix = cond do
      nursing > 0 and psw > 0 and housekeeping > 0 -> "nursing+psw+housekeeping"
      nursing > 0 and psw > 0 -> "nursing+psw"
      psw > 0 and housekeeping > 0 -> "psw+housekeeping"
      psw > 0 -> "psw_only"
      housekeeping > 0 -> "housekeeping_only"
      true -> "no_formal_services"
    end

    pc_cat = personal_care_category_for(input[:province])
    psw_rate = service_rate(services, input[:province], pc_cat)
    house_cat = if input[:agency_vs_private] == "agency", do: "Cleaning_Service_Agency", else: "Housekeeper_Private"
    house_rate = service_rate(services, input[:province], house_cat)
    nursing_rate = service_rate(services, input[:province], "LPN_RPN")

    private_monthly = (psw * psw_rate + housekeeping * house_rate + nursing * nursing_rate) * @weeks_per_month

    subsidy_hours =
      if input[:include_subsidy] do
        min(subsidy_hours_awarded(subsidies, input[:province], input[:adl_katz_score]), psw)
      else
        0.0
      end
    subsidy_value = subsidy_hours * psw_rate * @weeks_per_month
    oop_monthly = max(0.0, private_monthly - subsidy_value)
    oop_annual = oop_monthly * 12.0

    pp = Map.get(@provincial_factors, input[:province], @provincial_factors["ON"])
    fed_threshold = min(input[:net_family_income_cad] * @metc_floor_frac, @metc_abs_floor)
    metc_fed = max(0.0, oop_annual - fed_threshold) * @metc_federal_rate
    prov_threshold = min(input[:net_family_income_cad] * @metc_floor_frac, pp.metc_floor)
    metc_prov = max(0.0, oop_annual - prov_threshold) * pp.metc_rate
    metc_credit = metc_fed + metc_prov

    dtc_credit =
      if input[:has_dtc] or input[:cognitive_status] == "severe" do
        @dtc_base * @metc_federal_rate + pp.dtc_base * pp.metc_rate
      else
        0.0
      end

    ccc_credit =
      if input[:household_composition] in ["with_spouse", "with_adult_child", "multigen"] and psw >= 10 do
        income = input[:net_family_income_cad]
        phase_factor = cond do
          income <= @ccc_phase_start -> 1.0
          income >= @ccc_phase_end -> 0.0
          true -> 1.0 - (income - @ccc_phase_start) / (@ccc_phase_end - @ccc_phase_start)
        end
        (@ccc_caregiver_base * @metc_federal_rate + pp.ccc_base * pp.metc_rate) * phase_factor
      else
        0.0
      end

    vip_credit = if input[:is_veteran], do: @vip_housekeeping + @vip_personal_care, else: 0.0
    total_credits = metc_credit + dtc_credit + ccc_credit + vip_credit
    oop_after_annual = max(0.0, oop_annual - total_credits)
    oop_after_monthly = oop_after_annual / 12.0

    total_hours = psw + housekeeping + nursing
    all_psw_monthly = total_hours * psw_rate * @weeks_per_month
    hybrid_savings = all_psw_monthly - private_monthly

    scope_warnings =
      if input[:adl_katz_score] <= 4 or input[:cognitive_status] in ["moderate", "severe"] do
        ["Personal care required: the recipient's ADL score or cognitive status indicates that personal care tasks (bathing, toileting, transfers) are needed. A housekeeper or cleaning service cannot legally substitute for a PSW/HCA in this scope. If a cleaning service is part of the plan, it must be in addition to, not instead of, personal support."]
      else
        []
      end

    employment_warnings =
      if input[:agency_vs_private] == "private" and (total_hours - subsidy_hours) >= 20 do
        ["At #{trunc(total_hours - subsidy_hours)} hours per week of privately-hired care in #{input[:province]}, the CRA employer-determination test is likely to classify the family as an employer."]
      else
        []
      end

    %{
      province: input[:province],
      tax_year: input[:tax_year],
      recommended_psw_hours_per_week: psw,
      recommended_housekeeping_hours_per_week: housekeeping,
      recommended_nursing_hours_per_week: nursing,
      recommended_service_mix: mix,
      psw_hourly_rate_cad: round2(psw_rate),
      housekeeping_hourly_rate_cad: round2(house_rate),
      nursing_hourly_rate_cad: round2(nursing_rate),
      private_pay_monthly_cad: round2(private_monthly),
      subsidy_hours_per_week_allocated: round1(subsidy_hours),
      subsidy_value_monthly_cad: round2(subsidy_value),
      out_of_pocket_before_credits_monthly_cad: round2(oop_monthly),
      metc_credit_value_cad: round2(metc_credit),
      dtc_credit_value_cad: round2(dtc_credit),
      ccc_credit_value_cad: round2(ccc_credit),
      vac_vip_credit_value_cad: round2(vip_credit),
      total_credits_value_cad: round2(total_credits),
      out_of_pocket_after_credits_monthly_cad: round2(oop_after_monthly),
      out_of_pocket_after_credits_annual_cad: round2(oop_after_annual),
      all_psw_cost_comparison_monthly_cad: round2(all_psw_monthly),
      hybrid_savings_vs_all_psw_monthly_cad: round2(hybrid_savings),
      scope_warnings: scope_warnings,
      employment_law_warnings: employment_warnings,
      currency: "CAD",
      disclaimer: @disclaimer
    }
  end

  def sample do
    calculate(%{
      adl_katz_score: 2,
      iadl_lawton_score: 1,
      province: "BC",
      household_composition: "with_spouse",
      cognitive_status: "moderate",
      mobility_status: "walker",
      primary_diagnosis_category: "dementia",
      informal_caregiver_hours_per_week: 20.0,
      net_family_income_cad: 72000.0,
      has_dtc: true
    })
  end
end
