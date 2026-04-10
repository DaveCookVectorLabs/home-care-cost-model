Gem::Specification.new do |spec|
  spec.name          = "home_care_cost_model"
  spec.version       = "0.1.0"
  spec.authors       = ["Dave Cook"]
  spec.email         = ["dave@binx.ca"]
  spec.summary       = "Reference cost model for Canadian home care service-mix decisions."
  spec.description   = "Ruby port of the Home Care Cost Model reference implementation. Calculates recommended PSW, housekeeping, and nursing hours, private-pay cost, subsidised hours, and the 2026 federal/provincial tax relief stack for Canadian households."
  spec.homepage      = "https://github.com/DaveCookVectorLabs/home-care-cost-model"
  spec.license       = "MIT"
  spec.required_ruby_version = ">= 2.7.0"
  spec.files         = ["lib/home_care_cost_model.rb", "bin/home-care-cost-model"]
  spec.bindir        = "bin"
  spec.executables   = ["home-care-cost-model"]
  spec.require_paths = ["lib"]
  spec.metadata      = {
    "homepage_uri" => "https://github.com/DaveCookVectorLabs/home-care-cost-model",
    "source_code_uri" => "https://github.com/DaveCookVectorLabs/home-care-cost-model",
    "documentation_uri" => "https://www.binx.ca/guides/home-care-cost-model-guide.pdf",
  }
end
