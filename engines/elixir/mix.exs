defmodule HomeCareCostModel.MixProject do
  use Mix.Project

  def project do
    [
      app: :home_care_cost_model,
      version: "0.1.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      description: description(),
      package: package()
    ]
  end

  def application do
    [extra_applications: [:logger]]
  end

  defp deps do
    []
  end

  defp description do
    "Reference cost model for Canadian home care service-mix decisions (PSW, housekeeping, nursing) with 2026 tax relief stack and per-province subsidy eligibility."
  end

  defp package do
    [
      maintainers: ["Dave Cook"],
      licenses: ["MIT"],
      links: %{
        "GitHub" => "https://github.com/DaveCookVectorLabs/home-care-cost-model",
        "Working Paper" => "https://www.binx.ca/guides/home-care-cost-model-guide.pdf"
      },
      files: ~w(lib mix.exs README*)
    ]
  end
end
