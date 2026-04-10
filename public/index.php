<?php
declare(strict_types=1);

require_once __DIR__ . "/../engines/php/src/HomeCareCalculator.php";

use DaveCook\HomeCareCostModel\HomeCareCalculator;

$calc = new HomeCareCalculator(__DIR__ . "/../datasets");
$result = null;
$error = null;

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    try {
        $input = [
            "adl_katz_score" => (int) ($_POST["adl"] ?? 3),
            "iadl_lawton_score" => (int) ($_POST["iadl"] ?? 3),
            "province" => $_POST["province"] ?? "ON",
            "household_composition" => $_POST["household"] ?? "alone",
            "cognitive_status" => $_POST["cognitive"] ?? "intact",
            "mobility_status" => $_POST["mobility"] ?? "independent",
            "primary_diagnosis_category" => $_POST["diagnosis"] ?? "frailty",
            "informal_caregiver_hours_per_week" => (float) ($_POST["informal"] ?? 0),
            "net_family_income_cad" => (float) ($_POST["income"] ?? 60000),
            "is_veteran" => isset($_POST["veteran"]),
            "has_dtc" => isset($_POST["dtc"]),
        ];
        $result = $calc->calculate($input);
    } catch (Throwable $e) {
        $error = $e->getMessage();
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Home Care Cost Model</title>
    <style>
        body {
            font-family: system-ui, -apple-system, Helvetica, sans-serif;
            max-width: 760px;
            margin: 2rem auto;
            padding: 1rem;
            color: #141414;
            background: #FAFAF8;
            line-height: 1.5;
        }
        h1 { font-size: 1.6rem; margin-bottom: 0.4rem; }
        h2 { font-size: 1.15rem; color: #5C5448; margin-top: 1.6rem; }
        form { display: grid; gap: 0.6rem; margin: 1rem 0; }
        label { display: flex; justify-content: space-between; align-items: center; }
        input, select { padding: 0.3rem; min-width: 10rem; }
        button {
            background: #141414;
            color: #FAFAF8;
            padding: 0.6rem 1.2rem;
            border: 0;
            cursor: pointer;
        }
        .disclaimer {
            background: #F5F3EF;
            padding: 0.8rem;
            border-left: 3px solid #E87A2D;
            font-size: 0.9rem;
            color: #5C5448;
        }
        .result { background: #FFF; padding: 1rem; border: 1px solid #D4D0C8; }
        .result dt { font-weight: bold; }
        .warning { color: #854F0B; background: #FAEEDA; padding: 0.6rem; }
    </style>
</head>
<body>
<h1>Home Care Cost Model</h1>
<p>A reference cost model for Canadian home care service-mix decisions.
See the <a href="https://www.binx.ca/guides/home-care-cost-model-guide.pdf">working paper</a> for methodology.</p>

<div class="disclaimer">
    Reference model only. Not clinical or financial advice; consult a
    regulated health professional or registered tax practitioner for
    individual decisions.
</div>

<form method="post">
    <label>Province
        <select name="province">
            <?php foreach (["ON","QC","BC","AB","SK","MB","NS","NB","NL","PE","YT","NT","NU"] as $p): ?>
                <option value="<?= $p ?>"><?= $p ?></option>
            <?php endforeach; ?>
        </select>
    </label>
    <label>Katz ADL score (0–6) <input type="number" name="adl" min="0" max="6" value="3"></label>
    <label>Lawton IADL score (0–8) <input type="number" name="iadl" min="0" max="8" value="3"></label>
    <label>Household
        <select name="household">
            <option value="alone">alone</option>
            <option value="with_spouse">with spouse</option>
            <option value="with_adult_child">with adult child</option>
            <option value="multigen">multigenerational</option>
        </select>
    </label>
    <label>Cognitive status
        <select name="cognitive">
            <option value="intact">intact</option>
            <option value="mild">mild impairment</option>
            <option value="moderate">moderate</option>
            <option value="severe">severe</option>
        </select>
    </label>
    <label>Mobility
        <select name="mobility">
            <option value="independent">independent</option>
            <option value="cane">cane</option>
            <option value="walker">walker</option>
            <option value="wheelchair">wheelchair</option>
            <option value="bedbound">bedbound</option>
        </select>
    </label>
    <label>Primary diagnosis
        <select name="diagnosis">
            <option value="frailty">frailty</option>
            <option value="dementia">dementia</option>
            <option value="stroke">stroke</option>
            <option value="parkinson">parkinson</option>
            <option value="post_surgical">post-surgical</option>
            <option value="mobility_only">mobility only</option>
            <option value="chronic_mixed">chronic mixed</option>
        </select>
    </label>
    <label>Informal caregiving (hours/week) <input type="number" name="informal" step="0.5" value="0"></label>
    <label>Net family income (CAD) <input type="number" name="income" value="60000"></label>
    <label>Veteran <input type="checkbox" name="veteran"></label>
    <label>Holds Disability Tax Credit <input type="checkbox" name="dtc"></label>
    <button type="submit">Compute</button>
</form>

<?php if ($error): ?>
    <div class="warning"><?= htmlspecialchars($error) ?></div>
<?php elseif ($result): ?>
    <h2>Result</h2>
    <div class="result">
        <dl>
            <?php foreach (["recommended_psw_hours_per_week","recommended_housekeeping_hours_per_week","recommended_nursing_hours_per_week","recommended_service_mix","private_pay_monthly_cad","subsidy_value_monthly_cad","out_of_pocket_before_credits_monthly_cad","metc_credit_value_cad","dtc_credit_value_cad","ccc_credit_value_cad","vac_vip_credit_value_cad","total_credits_value_cad","out_of_pocket_after_credits_monthly_cad","hybrid_savings_vs_all_psw_monthly_cad"] as $k): ?>
                <dt><?= htmlspecialchars($k) ?></dt>
                <dd><?= htmlspecialchars((string) $result[$k]) ?></dd>
            <?php endforeach; ?>
        </dl>
        <?php foreach ($result["scope_warnings"] as $w): ?>
            <div class="warning"><?= htmlspecialchars($w) ?></div>
        <?php endforeach; ?>
        <?php foreach ($result["employment_law_warnings"] as $w): ?>
            <div class="warning"><?= htmlspecialchars($w) ?></div>
        <?php endforeach; ?>
    </div>
<?php endif; ?>

<p style="font-size: 0.85rem; color: #7A7168; margin-top: 2rem;">
    Maintained by Dave Cook, <a href="https://www.binx.ca/residential.php">Binx Professional Cleaning</a>, North Bay and Sudbury, Ontario.
</p>
</body>
</html>
