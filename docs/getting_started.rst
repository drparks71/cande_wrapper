Getting Started
===============

Installation
------------

Install from PyPI (includes pre-built wheels for Windows and Linux)::

   pip install cande-wrapper

For visualization support (plotly)::

   pip install cande-wrapper[viz]

Quick Start
-----------

Run a CANDE analysis::

   from cande_wrapper import CandeEngine

   engine = CandeEngine(work_dir="path/to/my/models")
   result = engine.run("EX1")  # reads EX1.cid, writes EX1.out
   print(result.output_text)

Vehicle Definitions
-------------------

Standard AASHTO design vehicles::

   from cande_wrapper import Vehicle

   hs20 = Vehicle.hs20()          # AASHTO HS-20 (72 kip)
   hs25 = Vehicle.hs25()          # AASHTO HS-25 (90 kip)
   tandem = Vehicle.tandem()      # AASHTO design tandem (50 kip)
   cooper = Vehicle.cooper_e80()  # Cooper E-80 railroad (160 kip)

CANDE Input Files
-----------------

CANDE reads ``.cid`` input files (CANDE Input Data). These are fixed-format text files
with sections for master control, pipe type, mesh definitions, soil properties, and
load steps. Each problem is terminated by ``STOP``.

Output Files
------------

After ``engine.run("prefix")``, these files are created:

* ``prefix.out`` -- Main analysis output report
* ``prefix.log`` -- Engine log messages
* ``prefix_MeshGeom.xml`` -- Mesh geometry (for visualization)
* ``prefix_MeshResults.xml`` -- Mesh results (for visualization)
* ``prefix_BeamResults.xml`` -- Beam element results
