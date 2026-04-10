Home Care Cost Model
====================

A reference cost model and open dataset collection for Canadian home care
service-mix decisions. Quantifies the trade-off between Personal Support
Worker (PSW), housekeeping, and skilled nursing hours for an older adult
or person with a disability remaining at home. Covers all ten provinces
and three territories and incorporates 2026 federal and provincial tax
relief parameters (Medical Expense Tax Credit, Disability Tax Credit,
Canada Caregiver Credit, Veterans Independence Program).

**Reference model only. Not clinical or financial advice; consult a
regulated health professional or registered tax practitioner for
individual decisions.**

.. toctree::
   :maxdepth: 2
   :caption: Contents

   api
   datasets
   case-studies

Quick start
-----------

.. code-block:: bash

    pip install home-care-cost-model
    python -c "from engine import run_sample, print_result; print_result(run_sample())"

Working paper
-------------

The full working paper is available at
https://www.binx.ca/guides/home-care-cost-model-guide.pdf.

License
-------

MIT for code, CC BY 4.0 for datasets and the working paper.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
