// Home Care Cost Model — Go Engine
//
// Reference cost model for Canadian home care service-mix decisions.
// Port of the Python reference implementation in engines/python/engine.py.
//
// Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
// Maintainer: Dave Cook, Binx Professional Cleaning
//
// This reference model is not clinical or financial advice.
package main

import (
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

const (
	Version          = "0.1.0"
	WeeksPerMonth    = 4.345
	Disclaimer       = "Reference model only. Not clinical or financial advice; consult a regulated health professional or registered tax practitioner for individual decisions."
	MetcFederalRate  = 0.15
	MetcFloorFrac    = 0.03
	MetcAbsFloor     = 2759.0
	DtcBase          = 9872.0
	CccCaregiverBase = 8375.0
	CccPhaseStart    = 19666.0
	CccPhaseEnd      = 28041.0
	VipHousekeeping  = 3072.0
	VipPersonalCare  = 9324.0
)

// Reference data in-memory
var (
	servicesData   map[string]map[string]string // key "PROV|CATEGORY" → row
	subsidyData    map[string]map[string]string
	provincialData = map[string]struct {
		MetcRate    float64
		MetcFloor   float64
		DtcBase     float64
		CccBase     float64
	}{
		"ON": {0.0505, 2923, 10250, 5933},
		"QC": {0.1400, 2759, 3494, 1311},
		"BC": {0.0506, 2605, 9428, 5014},
		"AB": {0.1000, 2824, 16066, 12307},
		"SK": {0.1050, 2837, 10405, 10405},
		"MB": {0.1080, 1728, 6180, 3605},
		"NS": {0.0879, 1637, 7341, 4898},
		"NB": {0.0940, 2344, 8552, 5197},
		"NL": {0.0870, 2116, 7064, 3497},
		"PE": {0.0980, 1768, 6890, 2446},
		"YT": {0.0640, 2759, 9872, 8375},
		"NT": {0.0590, 2759, 14160, 5167},
		"NU": {0.0400, 2759, 15440, 5560},
	}
)

type CalculateRequest struct {
	AdlKatzScore                   int     `json:"adl_katz_score"`
	IadlLawtonScore                int     `json:"iadl_lawton_score"`
	Province                       string  `json:"province"`
	HouseholdComposition           string  `json:"household_composition"`
	CognitiveStatus                string  `json:"cognitive_status"`
	MobilityStatus                 string  `json:"mobility_status"`
	PrimaryDiagnosisCategory       string  `json:"primary_diagnosis_category"`
	InformalCaregiverHoursPerWeek  float64 `json:"informal_caregiver_hours_per_week"`
	NetFamilyIncomeCad             float64 `json:"net_family_income_cad"`
	IsVeteran                      bool    `json:"is_veteran"`
	HasDtc                         bool    `json:"has_dtc"`
	AgencyVsPrivate                string  `json:"agency_vs_private"`
	IncludeSubsidy                 *bool   `json:"include_subsidy"`
	TaxYear                        int     `json:"tax_year"`
}

type CalculateResult struct {
	Province                             string   `json:"province"`
	TaxYear                              int      `json:"tax_year"`
	RecommendedPswHoursPerWeek           float64  `json:"recommended_psw_hours_per_week"`
	RecommendedHousekeepingHoursPerWeek  float64  `json:"recommended_housekeeping_hours_per_week"`
	RecommendedNursingHoursPerWeek       float64  `json:"recommended_nursing_hours_per_week"`
	RecommendedServiceMix                string   `json:"recommended_service_mix"`
	PswHourlyRateCad                     float64  `json:"psw_hourly_rate_cad"`
	HousekeepingHourlyRateCad            float64  `json:"housekeeping_hourly_rate_cad"`
	NursingHourlyRateCad                 float64  `json:"nursing_hourly_rate_cad"`
	PrivatePayMonthlyCad                 float64  `json:"private_pay_monthly_cad"`
	SubsidyHoursPerWeekAllocated         float64  `json:"subsidy_hours_per_week_allocated"`
	SubsidyValueMonthlyCad               float64  `json:"subsidy_value_monthly_cad"`
	OutOfPocketBeforeCreditsMonthlyCad   float64  `json:"out_of_pocket_before_credits_monthly_cad"`
	MetcCreditValueCad                   float64  `json:"metc_credit_value_cad"`
	DtcCreditValueCad                    float64  `json:"dtc_credit_value_cad"`
	CccCreditValueCad                    float64  `json:"ccc_credit_value_cad"`
	VacVipCreditValueCad                 float64  `json:"vac_vip_credit_value_cad"`
	TotalCreditsValueCad                 float64  `json:"total_credits_value_cad"`
	OutOfPocketAfterCreditsMonthlyCad    float64  `json:"out_of_pocket_after_credits_monthly_cad"`
	OutOfPocketAfterCreditsAnnualCad     float64  `json:"out_of_pocket_after_credits_annual_cad"`
	AllPswCostComparisonMonthlyCad       float64  `json:"all_psw_cost_comparison_monthly_cad"`
	HybridSavingsVsAllPswMonthlyCad      float64  `json:"hybrid_savings_vs_all_psw_monthly_cad"`
	ScopeWarnings                        []string `json:"scope_warnings"`
	EmploymentLawWarnings                []string `json:"employment_law_warnings"`
	Currency                             string   `json:"currency"`
	Disclaimer                           string   `json:"disclaimer"`
}

func personalCareCategoryFor(prov string) string {
	switch prov {
	case "ON", "QC":
		return "PSW"
	case "BC", "AB", "SK", "MB":
		return "HCA"
	default:
		return "HSW"
	}
}

func cognitiveBump(c string) float64 {
	return map[string]float64{"intact": 0, "mild": 3, "moderate": 8, "severe": 14}[c]
}

func mobilityBump(m string) float64 {
	return map[string]float64{"independent": 0, "cane": 0.5, "walker": 2, "wheelchair": 5, "bedbound": 12}[m]
}

func householdMod(h string) float64 {
	return map[string]float64{"alone": 3, "with_spouse": 1.5, "with_adult_child": 1, "multigen": 0.5}[h]
}

func diagnosisNursing(d string) float64 {
	return map[string]float64{
		"dementia": 0, "stroke": 4, "frailty": 0, "parkinson": 1,
		"post_surgical": 6, "mobility_only": 0, "chronic_mixed": 2,
	}[d]
}

func derivePswHours(adl int, cognitive, mobility string, informal float64) float64 {
	base := 7.0 * math.Max(0, float64(6-adl))
	base += cognitiveBump(cognitive)
	base += mobilityBump(mobility)
	credited := math.Min(informal*0.5, base*0.6)
	return round1(math.Max(0, base-credited))
}

func deriveHousekeepingHours(iadl int, household string) float64 {
	base := 2.0 * math.Max(0, float64(8-iadl))
	base += householdMod(household)
	return round1(math.Max(0, base))
}

func deriveNursingHours(diagnosis, cognitive string) float64 {
	base := diagnosisNursing(diagnosis)
	if cognitive == "severe" {
		base += 1.0
	}
	return round1(math.Max(0, base))
}

func scopeGateWarnings(adl int, cognitive, diagnosis, mobility string) []string {
	w := []string{}
	if adl <= 4 || cognitive == "moderate" || cognitive == "severe" {
		w = append(w, "Personal care required: the recipient's ADL score or cognitive status indicates that personal care tasks (bathing, toileting, transfers) are needed. A housekeeper or cleaning service cannot legally substitute for a PSW/HCA in this scope. If a cleaning service is part of the plan, it must be in addition to, not instead of, personal support.")
	}
	if (mobility == "wheelchair" || mobility == "bedbound") && adl >= 5 {
		w = append(w, "Mobility status suggests transfer assistance despite a high ADL score. Verify ADL independence in transfers before excluding personal support hours.")
	}
	return w
}

func subsidyHoursAwarded(province string, adl int) float64 {
	row, ok := subsidyData[province]
	if !ok {
		return 0
	}
	moderate, _ := strconv.ParseFloat(row["typical_psw_hours_per_week_moderate"], 64)
	high, _ := strconv.ParseFloat(row["typical_psw_hours_per_week_high"], 64)
	if adl >= 5 {
		return 0
	}
	if adl <= 1 {
		return round1(high)
	}
	alpha := float64(4-adl) / 3.0
	return round1(moderate + alpha*(high-moderate))
}

func serviceRate(province, category string) float64 {
	row, ok := servicesData[province+"|"+category]
	if !ok {
		return 0
	}
	v, _ := strconv.ParseFloat(row["private_pay_rate_cad_median"], 64)
	return v
}

func agencyMarkup(province string) float64 {
	for k, row := range servicesData {
		if strings.HasPrefix(k, province+"|") {
			v, _ := strconv.ParseFloat(row["agency_markup_typical"], 64)
			if v > 0 {
				return v
			}
		}
	}
	return 1.35
}

func Calculate(req CalculateRequest) CalculateResult {
	if req.TaxYear == 0 {
		req.TaxYear = 2026
	}
	if req.HouseholdComposition == "" {
		req.HouseholdComposition = "alone"
	}
	if req.CognitiveStatus == "" {
		req.CognitiveStatus = "intact"
	}
	if req.MobilityStatus == "" {
		req.MobilityStatus = "independent"
	}
	if req.PrimaryDiagnosisCategory == "" {
		req.PrimaryDiagnosisCategory = "frailty"
	}
	if req.AgencyVsPrivate == "" {
		req.AgencyVsPrivate = "private"
	}
	includeSubsidy := true
	if req.IncludeSubsidy != nil {
		includeSubsidy = *req.IncludeSubsidy
	}
	if req.NetFamilyIncomeCad == 0 {
		req.NetFamilyIncomeCad = 60000
	}

	pswHours := derivePswHours(req.AdlKatzScore, req.CognitiveStatus, req.MobilityStatus, req.InformalCaregiverHoursPerWeek)
	housekeepingHours := deriveHousekeepingHours(req.IadlLawtonScore, req.HouseholdComposition)
	nursingHours := deriveNursingHours(req.PrimaryDiagnosisCategory, req.CognitiveStatus)

	mix := "no_formal_services"
	if nursingHours > 0 && pswHours > 0 {
		if housekeepingHours > 0 {
			mix = "nursing+psw+housekeeping"
		} else {
			mix = "nursing+psw"
		}
	} else if pswHours > 0 && housekeepingHours > 0 {
		mix = "psw+housekeeping"
	} else if pswHours > 0 {
		mix = "psw_only"
	} else if housekeepingHours > 0 {
		mix = "housekeeping_only"
	}

	pcCat := personalCareCategoryFor(req.Province)
	pswRate := serviceRate(req.Province, pcCat)
	var houseCat string
	if req.AgencyVsPrivate == "agency" {
		houseCat = "Cleaning_Service_Agency"
	} else {
		houseCat = "Housekeeper_Private"
	}
	housekeepingRate := serviceRate(req.Province, houseCat)
	nursingRate := serviceRate(req.Province, "LPN_RPN")

	if req.AgencyVsPrivate == "agency" {
		markup := agencyMarkup(req.Province)
		pswRate = round2(pswRate * markup)
		nursingRate = round2(nursingRate * markup)
	}

	privateMonthly := (pswHours*pswRate + housekeepingHours*housekeepingRate + nursingHours*nursingRate) * WeeksPerMonth

	var subsidyHours, subsidyValue float64
	if includeSubsidy {
		subsidyHours = subsidyHoursAwarded(req.Province, req.AdlKatzScore)
		if subsidyHours > pswHours {
			subsidyHours = pswHours
		}
	}
	subsidyValue = subsidyHours * pswRate * WeeksPerMonth

	oopMonthly := math.Max(0, privateMonthly-subsidyValue)
	oopAnnual := oopMonthly * 12.0

	// Tax credits
	pp, hasProv := provincialData[req.Province]
	if !hasProv {
		pp = provincialData["ON"]
	}

	// METC
	fedThreshold := math.Min(req.NetFamilyIncomeCad*MetcFloorFrac, MetcAbsFloor)
	metcFedQualifying := math.Max(0, oopAnnual-fedThreshold)
	metcFed := metcFedQualifying * MetcFederalRate
	provThreshold := math.Min(req.NetFamilyIncomeCad*MetcFloorFrac, pp.MetcFloor)
	metcProvQualifying := math.Max(0, oopAnnual-provThreshold)
	metcProv := metcProvQualifying * pp.MetcRate

	// DTC
	var dtc float64
	if req.HasDtc || req.CognitiveStatus == "severe" {
		dtc = DtcBase*MetcFederalRate + pp.DtcBase*pp.MetcRate
	}

	// CCC
	var ccc float64
	if (req.HouseholdComposition == "with_spouse" || req.HouseholdComposition == "with_adult_child" || req.HouseholdComposition == "multigen") && pswHours >= 10 {
		phaseFactor := 1.0
		if req.NetFamilyIncomeCad > CccPhaseStart {
			if req.NetFamilyIncomeCad >= CccPhaseEnd {
				phaseFactor = 0
			} else {
				phaseFactor = 1.0 - (req.NetFamilyIncomeCad-CccPhaseStart)/(CccPhaseEnd-CccPhaseStart)
			}
		}
		ccc = (CccCaregiverBase*MetcFederalRate + pp.CccBase*pp.MetcRate) * phaseFactor
	}

	// VIP
	var vip float64
	if req.IsVeteran {
		vip = VipHousekeeping + VipPersonalCare
	}

	total := metcFed + metcProv + dtc + ccc + vip
	oopAfterAnnual := math.Max(0, oopAnnual-total)
	oopAfterMonthly := oopAfterAnnual / 12.0

	totalHours := pswHours + housekeepingHours + nursingHours
	allPswMonthly := totalHours * pswRate * WeeksPerMonth
	hybridSavings := allPswMonthly - privateMonthly

	scopeW := scopeGateWarnings(req.AdlKatzScore, req.CognitiveStatus, req.PrimaryDiagnosisCategory, req.MobilityStatus)
	employmentW := []string{}
	if req.AgencyVsPrivate == "private" && (totalHours-subsidyHours) >= 20 {
		employmentW = append(employmentW, fmt.Sprintf(
			"At %.0f hours per week of privately-hired care in %s, the CRA employer-determination test is likely to classify the family as an employer. Obligations may include CPP contributions, EI premiums, provincial WSIB or WorkSafe coverage, and T4 reporting. Agency arrangements transfer these obligations to the agency as employer of record.",
			totalHours-subsidyHours, req.Province,
		))
	}

	return CalculateResult{
		Province:                             req.Province,
		TaxYear:                              req.TaxYear,
		RecommendedPswHoursPerWeek:           pswHours,
		RecommendedHousekeepingHoursPerWeek:  housekeepingHours,
		RecommendedNursingHoursPerWeek:       nursingHours,
		RecommendedServiceMix:                mix,
		PswHourlyRateCad:                     round2(pswRate),
		HousekeepingHourlyRateCad:            round2(housekeepingRate),
		NursingHourlyRateCad:                 round2(nursingRate),
		PrivatePayMonthlyCad:                 round2(privateMonthly),
		SubsidyHoursPerWeekAllocated:         round1(subsidyHours),
		SubsidyValueMonthlyCad:               round2(subsidyValue),
		OutOfPocketBeforeCreditsMonthlyCad:   round2(oopMonthly),
		MetcCreditValueCad:                   round2(metcFed + metcProv),
		DtcCreditValueCad:                    round2(dtc),
		CccCreditValueCad:                    round2(ccc),
		VacVipCreditValueCad:                 round2(vip),
		TotalCreditsValueCad:                 round2(total),
		OutOfPocketAfterCreditsMonthlyCad:    round2(oopAfterMonthly),
		OutOfPocketAfterCreditsAnnualCad:     round2(oopAfterAnnual),
		AllPswCostComparisonMonthlyCad:       round2(allPswMonthly),
		HybridSavingsVsAllPswMonthlyCad:      round2(hybridSavings),
		ScopeWarnings:                        scopeW,
		EmploymentLawWarnings:                employmentW,
		Currency:                             "CAD",
		Disclaimer:                           Disclaimer,
	}
}

func round1(v float64) float64 { return math.Round(v*10) / 10 }
func round2(v float64) float64 { return math.Round(v*100) / 100 }

// Load reference CSVs at startup
func loadCSV(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	records, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(records) < 1 {
		return nil, fmt.Errorf("empty csv: %s", path)
	}
	headers := records[0]
	rows := []map[string]string{}
	for _, rec := range records[1:] {
		row := map[string]string{}
		for i, h := range headers {
			if i < len(rec) {
				row[h] = rec[i]
			}
		}
		rows = append(rows, row)
	}
	return rows, nil
}

func loadReferenceData() error {
	exe, _ := os.Executable()
	baseDir := filepath.Dir(exe)
	candidates := []string{
		"./datasets",
		"../../datasets",
		filepath.Join(baseDir, "datasets"),
		filepath.Join(baseDir, "..", "..", "datasets"),
	}
	var servicesPath, subsidyPath string
	for _, c := range candidates {
		if _, err := os.Stat(filepath.Join(c, "home_care_services_canada.csv")); err == nil {
			servicesPath = filepath.Join(c, "home_care_services_canada.csv")
			subsidyPath = filepath.Join(c, "home_care_subsidy_programs.csv")
			break
		}
	}
	if servicesPath == "" {
		return fmt.Errorf("datasets directory not found")
	}

	servicesData = map[string]map[string]string{}
	rows, err := loadCSV(servicesPath)
	if err != nil {
		return err
	}
	for _, row := range rows {
		key := row["jurisdiction_code"] + "|" + row["service_category"]
		servicesData[key] = row
	}

	subsidyData = map[string]map[string]string{}
	rows, err = loadCSV(subsidyPath)
	if err != nil {
		return err
	}
	for _, row := range rows {
		code := row["jurisdiction_code"]
		if _, ok := subsidyData[code]; !ok {
			subsidyData[code] = row
		}
	}
	return nil
}

func handleCalculate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req CalculateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	result := Calculate(req)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	resp := map[string]interface{}{
		"status":                    "ok",
		"engine":                    "go",
		"version":                   Version,
		"port":                      8003,
		"services_rows_loaded":      len(servicesData),
		"subsidy_rows_loaded":       len(subsidyData),
		"disclaimer":                Disclaimer,
	}
	json.NewEncoder(w).Encode(resp)
}

func runSample() {
	includeSub := true
	req := CalculateRequest{
		AdlKatzScore:                  2,
		IadlLawtonScore:               1,
		Province:                      "BC",
		HouseholdComposition:          "with_spouse",
		CognitiveStatus:               "moderate",
		MobilityStatus:                "walker",
		PrimaryDiagnosisCategory:      "dementia",
		InformalCaregiverHoursPerWeek: 20.0,
		NetFamilyIncomeCad:            72000.0,
		HasDtc:                        true,
		AgencyVsPrivate:               "private",
		IncludeSubsidy:                &includeSub,
		TaxYear:                       2026,
	}
	result := Calculate(req)
	b, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(b))
}

var sortedKeys = sort.StringSlice{}

func main() {
	var port string
	var serve, sample bool
	flag.StringVar(&port, "port", "8003", "HTTP server port")
	flag.BoolVar(&serve, "serve", false, "Run HTTP server")
	flag.BoolVar(&sample, "sample", false, "Run sample calculation")
	flag.Parse()

	if err := loadReferenceData(); err != nil {
		fmt.Fprintf(os.Stderr, "Warning: could not load reference data: %v\n", err)
	}

	if sample {
		runSample()
		return
	}
	if serve {
		http.HandleFunc("/calculate", handleCalculate)
		http.HandleFunc("/health", handleHealth)
		fmt.Printf("Home Care Cost Model (Go) listening on port %s\n", port)
		if err := http.ListenAndServe(":"+port, nil); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	} else {
		runSample()
	}
}
