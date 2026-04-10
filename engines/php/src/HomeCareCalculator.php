<?php
/**
 * Home Care Cost Model — PHP reference port
 *
 * Reference cost model for Canadian home care service-mix decisions.
 * Port of the Python reference implementation.
 *
 * Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
 * This reference model is not clinical or financial advice.
 */

declare(strict_types=1);

namespace DaveCook\HomeCareCostModel;

class HomeCareCalculator
{
    public const VERSION = "0.1.0";
    private const WEEKS_PER_MONTH = 4.345;
    public const DISCLAIMER = "Reference model only. Not clinical or financial advice; consult a regulated health professional or registered tax practitioner for individual decisions.";

    private const METC_FEDERAL_RATE = 0.15;
    private const METC_FLOOR_FRAC = 0.03;
    private const METC_ABS_FLOOR = 2759.0;
    private const DTC_BASE = 9872.0;
    private const CCC_CAREGIVER_BASE = 8375.0;
    private const CCC_PHASE_START = 19666.0;
    private const CCC_PHASE_END = 28041.0;
    private const VIP_HOUSEKEEPING = 3072.0;
    private const VIP_PERSONAL_CARE = 9324.0;

    private const PROVINCIAL_FACTORS = [
        "ON" => ["metc_rate" => 0.0505, "metc_floor" => 2923, "dtc_base" => 10250, "ccc_base" => 5933],
        "QC" => ["metc_rate" => 0.1400, "metc_floor" => 2759, "dtc_base" => 3494, "ccc_base" => 1311],
        "BC" => ["metc_rate" => 0.0506, "metc_floor" => 2605, "dtc_base" => 9428, "ccc_base" => 5014],
        "AB" => ["metc_rate" => 0.1000, "metc_floor" => 2824, "dtc_base" => 16066, "ccc_base" => 12307],
        "SK" => ["metc_rate" => 0.1050, "metc_floor" => 2837, "dtc_base" => 10405, "ccc_base" => 10405],
        "MB" => ["metc_rate" => 0.1080, "metc_floor" => 1728, "dtc_base" => 6180, "ccc_base" => 3605],
        "NS" => ["metc_rate" => 0.0879, "metc_floor" => 1637, "dtc_base" => 7341, "ccc_base" => 4898],
        "NB" => ["metc_rate" => 0.0940, "metc_floor" => 2344, "dtc_base" => 8552, "ccc_base" => 5197],
        "NL" => ["metc_rate" => 0.0870, "metc_floor" => 2116, "dtc_base" => 7064, "ccc_base" => 3497],
        "PE" => ["metc_rate" => 0.0980, "metc_floor" => 1768, "dtc_base" => 6890, "ccc_base" => 2446],
        "YT" => ["metc_rate" => 0.0640, "metc_floor" => 2759, "dtc_base" => 9872, "ccc_base" => 8375],
        "NT" => ["metc_rate" => 0.0590, "metc_floor" => 2759, "dtc_base" => 14160, "ccc_base" => 5167],
        "NU" => ["metc_rate" => 0.0400, "metc_floor" => 2759, "dtc_base" => 15440, "ccc_base" => 5560],
    ];

    private array $services = [];
    private array $subsidies = [];

    public function __construct(?string $datasetsDir = null)
    {
        $datasetsDir = $datasetsDir ?? $this->findDatasetsDir();
        if ($datasetsDir !== null) {
            $this->services = $this->loadCsv("$datasetsDir/home_care_services_canada.csv", ["jurisdiction_code", "service_category"]);
            $this->subsidies = $this->loadCsv("$datasetsDir/home_care_subsidy_programs.csv", ["jurisdiction_code"]);
        }
    }

    private function findDatasetsDir(): ?string
    {
        $candidates = [
            __DIR__ . "/../../../datasets",
            __DIR__ . "/../datasets",
            "./datasets",
        ];
        foreach ($candidates as $dir) {
            if (file_exists("$dir/home_care_services_canada.csv")) {
                return $dir;
            }
        }
        return null;
    }

    private function loadCsv(string $path, array $keyCols): array
    {
        $result = [];
        if (!file_exists($path)) return $result;
        $fh = fopen($path, "r");
        $headers = fgetcsv($fh);
        while (($row = fgetcsv($fh)) !== false) {
            $assoc = array_combine($headers, $row);
            $key = implode("|", array_map(fn($col) => $assoc[$col] ?? "", $keyCols));
            if (!isset($result[$key])) {
                $result[$key] = $assoc;
            }
        }
        fclose($fh);
        return $result;
    }

    private static function personalCareCategoryFor(string $prov): string
    {
        if ($prov === "ON" || $prov === "QC") return "PSW";
        if (in_array($prov, ["BC", "AB", "SK", "MB"], true)) return "HCA";
        return "HSW";
    }

    private static function cognitiveBump(string $c): float
    {
        return ["intact" => 0.0, "mild" => 3.0, "moderate" => 8.0, "severe" => 14.0][$c] ?? 0.0;
    }

    private static function mobilityBump(string $m): float
    {
        return ["independent" => 0.0, "cane" => 0.5, "walker" => 2.0, "wheelchair" => 5.0, "bedbound" => 12.0][$m] ?? 0.0;
    }

    private static function householdMod(string $h): float
    {
        return ["alone" => 3.0, "with_spouse" => 1.5, "with_adult_child" => 1.0, "multigen" => 0.5][$h] ?? 2.0;
    }

    private static function diagnosisNursing(string $d): float
    {
        return ["stroke" => 4.0, "parkinson" => 1.0, "post_surgical" => 6.0, "chronic_mixed" => 2.0][$d] ?? 0.0;
    }

    private static function derivePswHours(int $adl, string $cognitive, string $mobility, float $informal): float
    {
        $base = 7.0 * max(0, 6 - $adl) + self::cognitiveBump($cognitive) + self::mobilityBump($mobility);
        $credited = min($informal * 0.5, $base * 0.6);
        return round(max(0.0, $base - $credited), 1);
    }

    private static function deriveHousekeepingHours(int $iadl, string $household): float
    {
        $base = 2.0 * max(0, 8 - $iadl) + self::householdMod($household);
        return round(max(0.0, $base), 1);
    }

    private static function deriveNursingHours(string $diagnosis, string $cognitive): float
    {
        $base = self::diagnosisNursing($diagnosis);
        if ($cognitive === "severe") $base += 1.0;
        return round(max(0.0, $base), 1);
    }

    private function serviceRate(string $prov, string $category): float
    {
        $row = $this->services["$prov|$category"] ?? null;
        if ($row === null) return 0.0;
        return (float) ($row["private_pay_rate_cad_median"] ?? 0);
    }

    private function subsidyHoursAwarded(string $prov, int $adl): float
    {
        $row = $this->subsidies[$prov] ?? null;
        if ($row === null) return 0.0;
        $moderate = (float) ($row["typical_psw_hours_per_week_moderate"] ?? 0);
        $high = (float) ($row["typical_psw_hours_per_week_high"] ?? 0);
        if ($adl >= 5) return 0.0;
        if ($adl <= 1) return round($high, 1);
        $alpha = (4 - $adl) / 3.0;
        return round($moderate + $alpha * ($high - $moderate), 1);
    }

    public function calculate(array $input): array
    {
        $input = array_merge([
            "household_composition" => "alone",
            "cognitive_status" => "intact",
            "mobility_status" => "independent",
            "primary_diagnosis_category" => "frailty",
            "informal_caregiver_hours_per_week" => 0.0,
            "net_family_income_cad" => 60000.0,
            "is_veteran" => false,
            "has_dtc" => false,
            "agency_vs_private" => "private",
            "include_subsidy" => true,
            "tax_year" => 2026,
        ], $input);

        $pswHours = self::derivePswHours(
            (int) $input["adl_katz_score"], $input["cognitive_status"],
            $input["mobility_status"], (float) $input["informal_caregiver_hours_per_week"]
        );
        $houseHours = self::deriveHousekeepingHours((int) $input["iadl_lawton_score"], $input["household_composition"]);
        $nursingHours = self::deriveNursingHours($input["primary_diagnosis_category"], $input["cognitive_status"]);

        if ($nursingHours > 0 && $pswHours > 0) {
            $mix = $houseHours > 0 ? "nursing+psw+housekeeping" : "nursing+psw";
        } elseif ($pswHours > 0 && $houseHours > 0) {
            $mix = "psw+housekeeping";
        } elseif ($pswHours > 0) {
            $mix = "psw_only";
        } elseif ($houseHours > 0) {
            $mix = "housekeeping_only";
        } else {
            $mix = "no_formal_services";
        }

        $pcCat = self::personalCareCategoryFor($input["province"]);
        $pswRate = $this->serviceRate($input["province"], $pcCat);
        $houseCat = $input["agency_vs_private"] === "agency" ? "Cleaning_Service_Agency" : "Housekeeper_Private";
        $houseRate = $this->serviceRate($input["province"], $houseCat);
        $nursingRate = $this->serviceRate($input["province"], "LPN_RPN");

        $privateMonthly = ($pswHours * $pswRate + $houseHours * $houseRate + $nursingHours * $nursingRate) * self::WEEKS_PER_MONTH;

        $subsidyHours = $input["include_subsidy"]
            ? min($this->subsidyHoursAwarded($input["province"], (int) $input["adl_katz_score"]), $pswHours)
            : 0.0;
        $subsidyValue = $subsidyHours * $pswRate * self::WEEKS_PER_MONTH;
        $oopMonthly = max(0.0, $privateMonthly - $subsidyValue);
        $oopAnnual = $oopMonthly * 12.0;

        $pp = self::PROVINCIAL_FACTORS[$input["province"]] ?? self::PROVINCIAL_FACTORS["ON"];
        $fedThreshold = min($input["net_family_income_cad"] * self::METC_FLOOR_FRAC, self::METC_ABS_FLOOR);
        $metcFed = max(0.0, $oopAnnual - $fedThreshold) * self::METC_FEDERAL_RATE;
        $provThreshold = min($input["net_family_income_cad"] * self::METC_FLOOR_FRAC, $pp["metc_floor"]);
        $metcProv = max(0.0, $oopAnnual - $provThreshold) * $pp["metc_rate"];
        $metcCredit = $metcFed + $metcProv;

        $dtcCredit = ($input["has_dtc"] || $input["cognitive_status"] === "severe")
            ? self::DTC_BASE * self::METC_FEDERAL_RATE + $pp["dtc_base"] * $pp["metc_rate"]
            : 0.0;

        $cccCredit = 0.0;
        if (in_array($input["household_composition"], ["with_spouse", "with_adult_child", "multigen"], true) && $pswHours >= 10) {
            $income = (float) $input["net_family_income_cad"];
            if ($income <= self::CCC_PHASE_START) {
                $phaseFactor = 1.0;
            } elseif ($income >= self::CCC_PHASE_END) {
                $phaseFactor = 0.0;
            } else {
                $phaseFactor = 1.0 - ($income - self::CCC_PHASE_START) / (self::CCC_PHASE_END - self::CCC_PHASE_START);
            }
            $cccCredit = (self::CCC_CAREGIVER_BASE * self::METC_FEDERAL_RATE + $pp["ccc_base"] * $pp["metc_rate"]) * $phaseFactor;
        }

        $vipCredit = $input["is_veteran"] ? (self::VIP_HOUSEKEEPING + self::VIP_PERSONAL_CARE) : 0.0;
        $totalCredits = $metcCredit + $dtcCredit + $cccCredit + $vipCredit;
        $oopAfterAnnual = max(0.0, $oopAnnual - $totalCredits);
        $oopAfterMonthly = $oopAfterAnnual / 12.0;

        $totalHours = $pswHours + $houseHours + $nursingHours;
        $allPswMonthly = $totalHours * $pswRate * self::WEEKS_PER_MONTH;
        $hybridSavings = $allPswMonthly - $privateMonthly;

        $scopeWarnings = [];
        if ((int) $input["adl_katz_score"] <= 4 || in_array($input["cognitive_status"], ["moderate", "severe"], true)) {
            $scopeWarnings[] = "Personal care required: the recipient's ADL score or cognitive status indicates that personal care tasks (bathing, toileting, transfers) are needed. A housekeeper or cleaning service cannot legally substitute for a PSW/HCA in this scope. If a cleaning service is part of the plan, it must be in addition to, not instead of, personal support.";
        }

        $employmentWarnings = [];
        if ($input["agency_vs_private"] === "private" && ($totalHours - $subsidyHours) >= 20) {
            $employmentWarnings[] = sprintf(
                "At %.0f hours per week of privately-hired care in %s, the CRA employer-determination test is likely to classify the family as an employer.",
                $totalHours - $subsidyHours, $input["province"]
            );
        }

        return [
            "province" => $input["province"],
            "tax_year" => $input["tax_year"],
            "recommended_psw_hours_per_week" => $pswHours,
            "recommended_housekeeping_hours_per_week" => $houseHours,
            "recommended_nursing_hours_per_week" => $nursingHours,
            "recommended_service_mix" => $mix,
            "psw_hourly_rate_cad" => round($pswRate, 2),
            "housekeeping_hourly_rate_cad" => round($houseRate, 2),
            "nursing_hourly_rate_cad" => round($nursingRate, 2),
            "private_pay_monthly_cad" => round($privateMonthly, 2),
            "subsidy_hours_per_week_allocated" => round($subsidyHours, 1),
            "subsidy_value_monthly_cad" => round($subsidyValue, 2),
            "out_of_pocket_before_credits_monthly_cad" => round($oopMonthly, 2),
            "metc_credit_value_cad" => round($metcCredit, 2),
            "dtc_credit_value_cad" => round($dtcCredit, 2),
            "ccc_credit_value_cad" => round($cccCredit, 2),
            "vac_vip_credit_value_cad" => round($vipCredit, 2),
            "total_credits_value_cad" => round($totalCredits, 2),
            "out_of_pocket_after_credits_monthly_cad" => round($oopAfterMonthly, 2),
            "out_of_pocket_after_credits_annual_cad" => round($oopAfterAnnual, 2),
            "all_psw_cost_comparison_monthly_cad" => round($allPswMonthly, 2),
            "hybrid_savings_vs_all_psw_monthly_cad" => round($hybridSavings, 2),
            "scope_warnings" => $scopeWarnings,
            "employment_law_warnings" => $employmentWarnings,
            "currency" => "CAD",
            "disclaimer" => self::DISCLAIMER,
        ];
    }
}

// CLI mode
if (PHP_SAPI === "cli" && isset($argv) && realpath($argv[0]) === __FILE__) {
    $calc = new HomeCareCalculator();
    $result = $calc->calculate([
        "adl_katz_score" => 2,
        "iadl_lawton_score" => 1,
        "province" => "BC",
        "household_composition" => "with_spouse",
        "cognitive_status" => "moderate",
        "mobility_status" => "walker",
        "primary_diagnosis_category" => "dementia",
        "informal_caregiver_hours_per_week" => 20.0,
        "net_family_income_cad" => 72000.0,
        "has_dtc" => true,
    ]);
    echo "Home Care Cost Model — PHP Engine v" . HomeCareCalculator::VERSION . PHP_EOL;
    echo "======================================================" . PHP_EOL;
    foreach ($result as $k => $v) {
        if (is_array($v)) $v = json_encode($v);
        if (is_bool($v)) $v = $v ? "true" : "false";
        echo sprintf("%-45s %s\n", $k, $v);
    }
}
