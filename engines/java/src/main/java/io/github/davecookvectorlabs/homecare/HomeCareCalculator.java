package io.github.davecookvectorlabs.homecare;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Home Care Cost Model — Java reference port.
 *
 * Reference cost model for Canadian home care service-mix decisions.
 * Port of the Python reference implementation.
 *
 * Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
 * This reference model is not clinical or financial advice.
 */
public final class HomeCareCalculator {

    public static final String VERSION = "0.1.0";
    public static final String DISCLAIMER =
        "Reference model only. Not clinical or financial advice; consult a regulated health professional or registered tax practitioner for individual decisions.";

    private static final double WEEKS_PER_MONTH = 4.345;
    private static final double METC_FEDERAL_RATE = 0.15;
    private static final double METC_FLOOR_FRAC = 0.03;
    private static final double METC_ABS_FLOOR = 2759.0;
    private static final double DTC_BASE = 9872.0;
    private static final double CCC_CAREGIVER_BASE = 8375.0;
    private static final double CCC_PHASE_START = 19666.0;
    private static final double CCC_PHASE_END = 28041.0;
    private static final double VIP_HOUSEKEEPING = 3072.0;
    private static final double VIP_PERSONAL_CARE = 9324.0;

    private static final Map<String, double[]> PROVINCIAL = new HashMap<>();
    static {
        // [metc_rate, metc_floor, dtc_base, ccc_base]
        PROVINCIAL.put("ON", new double[]{0.0505, 2923, 10250, 5933});
        PROVINCIAL.put("QC", new double[]{0.1400, 2759, 3494, 1311});
        PROVINCIAL.put("BC", new double[]{0.0506, 2605, 9428, 5014});
        PROVINCIAL.put("AB", new double[]{0.1000, 2824, 16066, 12307});
        PROVINCIAL.put("SK", new double[]{0.1050, 2837, 10405, 10405});
        PROVINCIAL.put("MB", new double[]{0.1080, 1728, 6180, 3605});
        PROVINCIAL.put("NS", new double[]{0.0879, 1637, 7341, 4898});
        PROVINCIAL.put("NB", new double[]{0.0940, 2344, 8552, 5197});
        PROVINCIAL.put("NL", new double[]{0.0870, 2116, 7064, 3497});
        PROVINCIAL.put("PE", new double[]{0.0980, 1768, 6890, 2446});
        PROVINCIAL.put("YT", new double[]{0.0640, 2759, 9872, 8375});
        PROVINCIAL.put("NT", new double[]{0.0590, 2759, 14160, 5167});
        PROVINCIAL.put("NU", new double[]{0.0400, 2759, 15440, 5560});
    }

    private final Map<String, Map<String, String>> services;
    private final Map<String, Map<String, String>> subsidies;

    public HomeCareCalculator() {
        this.services = new HashMap<>();
        this.subsidies = new HashMap<>();
        loadReferenceData();
    }

    private void loadReferenceData() {
        String[] candidates = {"./datasets", "../../datasets", "../../../datasets"};
        Path servicesPath = null;
        Path subsidyPath = null;
        for (String c : candidates) {
            Path p = Paths.get(c, "home_care_services_canada.csv");
            if (Files.exists(p)) {
                servicesPath = p;
                subsidyPath = Paths.get(c, "home_care_subsidy_programs.csv");
                break;
            }
        }
        if (servicesPath != null) {
            loadCsv(servicesPath, services, new String[]{"jurisdiction_code", "service_category"});
        }
        if (subsidyPath != null) {
            loadCsv(subsidyPath, subsidies, new String[]{"jurisdiction_code"});
        }
    }

    private void loadCsv(Path path, Map<String, Map<String, String>> target, String[] keyCols) {
        try (BufferedReader br = Files.newBufferedReader(path)) {
            String headerLine = br.readLine();
            if (headerLine == null) return;
            String[] headers = parseCsvLine(headerLine);
            String line;
            while ((line = br.readLine()) != null) {
                String[] fields = parseCsvLine(line);
                Map<String, String> row = new HashMap<>();
                for (int i = 0; i < headers.length && i < fields.length; i++) {
                    row.put(headers[i], fields[i]);
                }
                StringBuilder key = new StringBuilder();
                for (int i = 0; i < keyCols.length; i++) {
                    if (i > 0) key.append("|");
                    key.append(row.getOrDefault(keyCols[i], ""));
                }
                target.putIfAbsent(key.toString(), row);
            }
        } catch (IOException e) {
            // silent — reference data is optional for library users
        }
    }

    private static String[] parseCsvLine(String line) {
        List<String> fields = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inQuotes = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') inQuotes = !inQuotes;
            else if (c == ',' && !inQuotes) { fields.add(current.toString()); current.setLength(0); }
            else current.append(c);
        }
        fields.add(current.toString());
        return fields.toArray(new String[0]);
    }

    private static String personalCareCategoryFor(String prov) {
        if (prov.equals("ON") || prov.equals("QC")) return "PSW";
        if (prov.equals("BC") || prov.equals("AB") || prov.equals("SK") || prov.equals("MB")) return "HCA";
        return "HSW";
    }

    private static double cognitiveBump(String c) {
        switch (c) {
            case "intact": return 0.0;
            case "mild": return 3.0;
            case "moderate": return 8.0;
            case "severe": return 14.0;
            default: return 0.0;
        }
    }

    private static double mobilityBump(String m) {
        switch (m) {
            case "independent": return 0.0;
            case "cane": return 0.5;
            case "walker": return 2.0;
            case "wheelchair": return 5.0;
            case "bedbound": return 12.0;
            default: return 0.0;
        }
    }

    private static double householdMod(String h) {
        switch (h) {
            case "alone": return 3.0;
            case "with_spouse": return 1.5;
            case "with_adult_child": return 1.0;
            case "multigen": return 0.5;
            default: return 2.0;
        }
    }

    private static double diagnosisNursing(String d) {
        switch (d) {
            case "stroke": return 4.0;
            case "parkinson": return 1.0;
            case "post_surgical": return 6.0;
            case "chronic_mixed": return 2.0;
            default: return 0.0;
        }
    }

    public static double derivePswHours(int adl, String cognitive, String mobility, double informal) {
        double base = 7.0 * Math.max(0, 6 - adl) + cognitiveBump(cognitive) + mobilityBump(mobility);
        double credited = Math.min(informal * 0.5, base * 0.6);
        return round1(Math.max(0.0, base - credited));
    }

    public static double deriveHousekeepingHours(int iadl, String household) {
        double base = 2.0 * Math.max(0, 8 - iadl) + householdMod(household);
        return round1(Math.max(0.0, base));
    }

    public static double deriveNursingHours(String diagnosis, String cognitive) {
        double base = diagnosisNursing(diagnosis);
        if (cognitive.equals("severe")) base += 1.0;
        return round1(Math.max(0.0, base));
    }

    private static double round1(double v) { return Math.round(v * 10.0) / 10.0; }
    private static double round2(double v) { return Math.round(v * 100.0) / 100.0; }

    private double serviceRate(String prov, String category) {
        Map<String, String> row = services.get(prov + "|" + category);
        if (row == null) return 0.0;
        try {
            return Double.parseDouble(row.getOrDefault("private_pay_rate_cad_median", "0"));
        } catch (NumberFormatException e) { return 0.0; }
    }

    private double subsidyHoursAwarded(String prov, int adl) {
        Map<String, String> row = subsidies.get(prov);
        if (row == null) return 0.0;
        double moderate, high;
        try {
            moderate = Double.parseDouble(row.getOrDefault("typical_psw_hours_per_week_moderate", "0"));
            high = Double.parseDouble(row.getOrDefault("typical_psw_hours_per_week_high", "0"));
        } catch (NumberFormatException e) { return 0.0; }
        if (adl >= 5) return 0.0;
        if (adl <= 1) return round1(high);
        double alpha = (4 - adl) / 3.0;
        return round1(moderate + alpha * (high - moderate));
    }

    public static final class CalculateInput {
        public int adlKatzScore;
        public int iadlLawtonScore;
        public String province;
        public String householdComposition = "alone";
        public String cognitiveStatus = "intact";
        public String mobilityStatus = "independent";
        public String primaryDiagnosisCategory = "frailty";
        public double informalCaregiverHoursPerWeek = 0.0;
        public double netFamilyIncomeCad = 60000.0;
        public boolean isVeteran = false;
        public boolean hasDtc = false;
        public String agencyVsPrivate = "private";
        public boolean includeSubsidy = true;
        public int taxYear = 2026;
    }

    public static final class CalculateResult {
        public String province;
        public int taxYear;
        public double recommendedPswHoursPerWeek;
        public double recommendedHousekeepingHoursPerWeek;
        public double recommendedNursingHoursPerWeek;
        public String recommendedServiceMix;
        public double pswHourlyRateCad;
        public double housekeepingHourlyRateCad;
        public double nursingHourlyRateCad;
        public double privatePayMonthlyCad;
        public double subsidyHoursPerWeekAllocated;
        public double subsidyValueMonthlyCad;
        public double outOfPocketBeforeCreditsMonthlyCad;
        public double metcCreditValueCad;
        public double dtcCreditValueCad;
        public double cccCreditValueCad;
        public double vacVipCreditValueCad;
        public double totalCreditsValueCad;
        public double outOfPocketAfterCreditsMonthlyCad;
        public double outOfPocketAfterCreditsAnnualCad;
        public double allPswCostComparisonMonthlyCad;
        public double hybridSavingsVsAllPswMonthlyCad;
        public List<String> scopeWarnings = new ArrayList<>();
        public List<String> employmentLawWarnings = new ArrayList<>();
        public String currency = "CAD";
        public String disclaimer = DISCLAIMER;
    }

    public CalculateResult calculate(CalculateInput in) {
        double psw = derivePswHours(in.adlKatzScore, in.cognitiveStatus, in.mobilityStatus, in.informalCaregiverHoursPerWeek);
        double house = deriveHousekeepingHours(in.iadlLawtonScore, in.householdComposition);
        double nursing = deriveNursingHours(in.primaryDiagnosisCategory, in.cognitiveStatus);

        String mix;
        if (nursing > 0 && psw > 0) mix = house > 0 ? "nursing+psw+housekeeping" : "nursing+psw";
        else if (psw > 0 && house > 0) mix = "psw+housekeeping";
        else if (psw > 0) mix = "psw_only";
        else if (house > 0) mix = "housekeeping_only";
        else mix = "no_formal_services";

        String pcCat = personalCareCategoryFor(in.province);
        double pswRate = serviceRate(in.province, pcCat);
        String houseCat = in.agencyVsPrivate.equals("agency") ? "Cleaning_Service_Agency" : "Housekeeper_Private";
        double houseRate = serviceRate(in.province, houseCat);
        double nursingRate = serviceRate(in.province, "LPN_RPN");

        double privateMonthly = (psw * pswRate + house * houseRate + nursing * nursingRate) * WEEKS_PER_MONTH;
        double subsidyHours = in.includeSubsidy ? Math.min(subsidyHoursAwarded(in.province, in.adlKatzScore), psw) : 0.0;
        double subsidyValue = subsidyHours * pswRate * WEEKS_PER_MONTH;
        double oopMonthly = Math.max(0.0, privateMonthly - subsidyValue);
        double oopAnnual = oopMonthly * 12.0;

        double[] pp = PROVINCIAL.getOrDefault(in.province, PROVINCIAL.get("ON"));
        double fedThreshold = Math.min(in.netFamilyIncomeCad * METC_FLOOR_FRAC, METC_ABS_FLOOR);
        double metcFed = Math.max(0, oopAnnual - fedThreshold) * METC_FEDERAL_RATE;
        double provThreshold = Math.min(in.netFamilyIncomeCad * METC_FLOOR_FRAC, pp[1]);
        double metcProv = Math.max(0, oopAnnual - provThreshold) * pp[0];
        double metcCredit = metcFed + metcProv;

        double dtcCredit = (in.hasDtc || in.cognitiveStatus.equals("severe"))
            ? (DTC_BASE * METC_FEDERAL_RATE + pp[2] * pp[0]) : 0.0;

        double cccCredit = 0.0;
        boolean eligibleHousehold = in.householdComposition.equals("with_spouse")
            || in.householdComposition.equals("with_adult_child")
            || in.householdComposition.equals("multigen");
        if (eligibleHousehold && psw >= 10) {
            double phaseFactor;
            if (in.netFamilyIncomeCad <= CCC_PHASE_START) phaseFactor = 1.0;
            else if (in.netFamilyIncomeCad >= CCC_PHASE_END) phaseFactor = 0.0;
            else phaseFactor = 1.0 - (in.netFamilyIncomeCad - CCC_PHASE_START) / (CCC_PHASE_END - CCC_PHASE_START);
            cccCredit = (CCC_CAREGIVER_BASE * METC_FEDERAL_RATE + pp[3] * pp[0]) * phaseFactor;
        }

        double vipCredit = in.isVeteran ? (VIP_HOUSEKEEPING + VIP_PERSONAL_CARE) : 0.0;
        double totalCredits = metcCredit + dtcCredit + cccCredit + vipCredit;
        double oopAfterAnnual = Math.max(0.0, oopAnnual - totalCredits);
        double oopAfterMonthly = oopAfterAnnual / 12.0;

        double totalHours = psw + house + nursing;
        double allPswMonthly = totalHours * pswRate * WEEKS_PER_MONTH;
        double hybridSavings = allPswMonthly - privateMonthly;

        CalculateResult r = new CalculateResult();
        r.province = in.province;
        r.taxYear = in.taxYear;
        r.recommendedPswHoursPerWeek = psw;
        r.recommendedHousekeepingHoursPerWeek = house;
        r.recommendedNursingHoursPerWeek = nursing;
        r.recommendedServiceMix = mix;
        r.pswHourlyRateCad = round2(pswRate);
        r.housekeepingHourlyRateCad = round2(houseRate);
        r.nursingHourlyRateCad = round2(nursingRate);
        r.privatePayMonthlyCad = round2(privateMonthly);
        r.subsidyHoursPerWeekAllocated = round1(subsidyHours);
        r.subsidyValueMonthlyCad = round2(subsidyValue);
        r.outOfPocketBeforeCreditsMonthlyCad = round2(oopMonthly);
        r.metcCreditValueCad = round2(metcCredit);
        r.dtcCreditValueCad = round2(dtcCredit);
        r.cccCreditValueCad = round2(cccCredit);
        r.vacVipCreditValueCad = round2(vipCredit);
        r.totalCreditsValueCad = round2(totalCredits);
        r.outOfPocketAfterCreditsMonthlyCad = round2(oopAfterMonthly);
        r.outOfPocketAfterCreditsAnnualCad = round2(oopAfterAnnual);
        r.allPswCostComparisonMonthlyCad = round2(allPswMonthly);
        r.hybridSavingsVsAllPswMonthlyCad = round2(hybridSavings);

        if (in.adlKatzScore <= 4 || in.cognitiveStatus.equals("moderate") || in.cognitiveStatus.equals("severe")) {
            r.scopeWarnings.add(
                "Personal care required: the recipient's ADL score or cognitive status indicates that personal care tasks (bathing, toileting, transfers) are needed. A housekeeper or cleaning service cannot legally substitute for a PSW/HCA in this scope. If a cleaning service is part of the plan, it must be in addition to, not instead of, personal support."
            );
        }
        if (in.agencyVsPrivate.equals("private") && (totalHours - subsidyHours) >= 20) {
            r.employmentLawWarnings.add(
                String.format("At %.0f hours per week of privately-hired care in %s, the CRA employer-determination test is likely to classify the family as an employer.",
                    totalHours - subsidyHours, in.province)
            );
        }
        return r;
    }

    public static void main(String[] args) {
        HomeCareCalculator calc = new HomeCareCalculator();
        CalculateInput input = new CalculateInput();
        input.adlKatzScore = 2;
        input.iadlLawtonScore = 1;
        input.province = "BC";
        input.householdComposition = "with_spouse";
        input.cognitiveStatus = "moderate";
        input.mobilityStatus = "walker";
        input.primaryDiagnosisCategory = "dementia";
        input.informalCaregiverHoursPerWeek = 20.0;
        input.netFamilyIncomeCad = 72000.0;
        input.hasDtc = true;

        CalculateResult r = calc.calculate(input);
        System.out.println("Home Care Cost Model — Java Engine v" + VERSION);
        System.out.println("======================================================");
        System.out.println("Jurisdiction: " + r.province + "   Tax year: " + r.taxYear);
        System.out.println("Recommended PSW hours/week:      " + r.recommendedPswHoursPerWeek);
        System.out.println("Recommended housekeeping h/w:    " + r.recommendedHousekeepingHoursPerWeek);
        System.out.println("Recommended nursing h/w:         " + r.recommendedNursingHoursPerWeek);
        System.out.println("Service mix:                     " + r.recommendedServiceMix);
        System.out.printf("Private pay monthly CAD:         $%.2f%n", r.privatePayMonthlyCad);
        System.out.printf("Subsidy value monthly CAD:       $%.2f%n", r.subsidyValueMonthlyCad);
        System.out.printf("OoP before credits monthly CAD:  $%.2f%n", r.outOfPocketBeforeCreditsMonthlyCad);
        System.out.printf("Tax credits annual CAD:          $%.2f%n", r.totalCreditsValueCad);
        System.out.printf("OoP after credits monthly CAD:   $%.2f%n", r.outOfPocketAfterCreditsMonthlyCad);
        System.out.printf("OoP after credits annual CAD:    $%.2f%n", r.outOfPocketAfterCreditsAnnualCad);
        System.out.printf("All-PSW comparison monthly CAD:  $%.2f%n", r.allPswCostComparisonMonthlyCad);
        System.out.printf("Hybrid savings monthly CAD:      $%.2f%n", r.hybridSavingsVsAllPswMonthlyCad);
        System.out.println();
        System.out.println("Disclaimer: " + DISCLAIMER);
    }
}
