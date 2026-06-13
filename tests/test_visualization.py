"""Unit tests for cande_wrapper.visualization — XML parsers and Plotly plots.

Uses small hand-built XML fixtures crafted to exercise every element type
(BEAM/QUAD/TRIA/INTF), boundary code, and plotting branch. plotly is required
(installed via the project venv).
"""
import textwrap
from pathlib import Path

import pytest

import cande_wrapper.visualization as viz


# ── XML fixtures ──────────────────────────────────────────────────────────────

MESH_GEOM_XML = textwrap.dedent("""\
    <CandeDataBase>
      <Control><Heading>Test Culvert Mesh</Heading></Control>
      <Geometry>
        <nodeCoord><nodeNumber>1</nodeNumber><nodeXCoord>0.0</nodeXCoord><nodeYCoord>0.0</nodeYCoord></nodeCoord>
        <nodeCoord><nodeNumber>2</nodeNumber><nodeXCoord>1.0</nodeXCoord><nodeYCoord>0.0</nodeYCoord></nodeCoord>
        <nodeCoord><nodeNumber>3</nodeNumber><nodeXCoord>1.0</nodeXCoord><nodeYCoord>1.0</nodeYCoord></nodeCoord>
        <nodeCoord><nodeNumber>4</nodeNumber><nodeXCoord>0.0</nodeXCoord><nodeYCoord>1.0</nodeYCoord></nodeCoord>
        <nodeCoord><nodeNumber>5</nodeNumber><nodeXCoord>2.0</nodeXCoord><nodeYCoord>0.5</nodeYCoord></nodeCoord>
        <elemConn><elemNumber>1</elemNumber><elemNode1>1</elemNode1><elemNode2>2</elemNode2><elemNode3>3</elemNode3><elemNode4>4</elemNode4><elemMatNum>1</elemMatNum><elemConstrIncr>0</elemConstrIncr><elemType>QUAD</elemType></elemConn>
        <elemConn><elemNumber>2</elemNumber><elemNode1>2</elemNode1><elemNode2>3</elemNode2><elemNode3>5</elemNode3><elemNode4>5</elemNode4><elemMatNum>2</elemMatNum><elemConstrIncr>0</elemConstrIncr><elemType>TRIA</elemType></elemConn>
        <elemConn><elemNumber>3</elemNumber><elemNode1>1</elemNode1><elemNode2>2</elemNode2><elemNode3>2</elemNode3><elemNode4>2</elemNode4><elemMatNum>3</elemMatNum><elemConstrIncr>0</elemConstrIncr><elemType>BEAM</elemType></elemConn>
        <elemConn><elemNumber>4</elemNumber><elemNode1>3</elemNode1><elemNode2>4</elemNode2><elemNode3>4</elemNode3><elemNode4>4</elemNode4><elemMatNum>4</elemMatNum><elemConstrIncr>0</elemConstrIncr><elemType>INTF</elemType></elemConn>
        <boundary><boundNumber>1</boundNumber><boundNode>1</boundNode><boundConstrIncr>0</boundConstrIncr><boundXCode>1</boundXCode><boundYCode>1</boundYCode><boundXForce>0.0</boundXForce><boundYForce>0.0</boundYForce><boundRotAngle>0.0</boundRotAngle></boundary>
        <boundary><boundNumber>2</boundNumber><boundNode>4</boundNode><boundConstrIncr>0</boundConstrIncr><boundXCode>0</boundXCode><boundYCode>0</boundYCode><boundXForce>5.0</boundXForce><boundYForce>0.0</boundYForce><boundRotAngle>0.0</boundRotAngle></boundary>
        <boundary><boundNumber>3</boundNumber><boundNode>999</boundNode><boundConstrIncr>0</boundConstrIncr><boundXCode>1</boundXCode><boundYCode>0</boundYCode><boundXForce>0.0</boundXForce><boundYForce>0.0</boundYForce><boundRotAngle>0.0</boundRotAngle></boundary>
      </Geometry>
    </CandeDataBase>
    """)

MESH_RESULTS_XML = textwrap.dedent("""\
    <CandeDataBase>
      <Control><Heading>Test Results</Heading></Control>
      <displacementData>
        <dispConstIncr>1</dispConstIncr>
        <nodeDisp><nodeDispNumber>1</nodeDispNumber><nodeXDisp>0.01</nodeXDisp><nodeYDisp>-0.02</nodeYDisp></nodeDisp>
        <nodeDisp><nodeDispNumber>3</nodeDispNumber><nodeXDisp>0.03</nodeXDisp><nodeYDisp>-0.04</nodeYDisp></nodeDisp>
        <nodeDisp><nodeDispNumber>999</nodeDispNumber><nodeXDisp>0.0</nodeXDisp><nodeYDisp>0.0</nodeYDisp></nodeDisp>
        <elemDisp><elemDispNumber>1</elemDispNumber><elemDispType>QUAD</elemDispType><st1>0.1</st1><st2>0.2</st2><st3>0.3</st3><st4>10.0</st4><st5>20.0</st5><st6>5.0</st6></elemDisp>
        <elemDisp><elemDispNumber>2</elemDispNumber><elemDispType>TRIA</elemDispType><st1>0.1</st1><st2>0.2</st2><st3>0.3</st3><st4>11.0</st4><st5>21.0</st5><st6>6.0</st6></elemDisp>
        <elemDisp><elemDispNumber>3</elemDispNumber><elemDispType>BEAM</elemDispType><st1>0</st1><st2>0</st2><st3>0</st3><st4>0</st4><st5>0</st5><st6>0</st6></elemDisp>
      </displacementData>
      <displacementData>
        <dispConstIncr>2</dispConstIncr>
        <nodeDisp><nodeDispNumber>1</nodeDispNumber><nodeXDisp>0.05</nodeXDisp><nodeYDisp>-0.06</nodeYDisp></nodeDisp>
        <elemDisp><elemDispNumber>1</elemDispNumber><elemDispType>QUAD</elemDispType><st1>0.2</st1><st2>0.3</st2><st3>0.4</st3><st4>12.0</st4><st5>22.0</st5><st6>7.0</st6></elemDisp>
      </displacementData>
    </CandeDataBase>
    """)


def _beam_result(rid, node, with_extra):
    extra = ""
    if with_extra:
        extra = "".join(f"<result{k}>{k * 1.5}</result{k}>" for k in range(10, 19))
    return textwrap.dedent(f"""\
        <resultsData>
          <resultId>{rid}</resultId><nodeNumber>{node}</nodeNumber>
          <elementNumber>{rid}</elementNumber><beamGroupNumber>1</beamGroupNumber>
          <pipeType>1</pipeType><xCoord>{node * 1.0}</xCoord><yCoord>0.0</yCoord>
          <xDisp>0.001</xDisp><yDisp>-0.002</yDisp>
          <bendingMoment>{node * 10.0}</bendingMoment><thrustForce>{node * 5.0}</thrustForce>
          <shearForce>{node * 2.0}</shearForce><normalPressure>1.0</normalPressure>
          <tangPressure>0.5</tangPressure>{extra}
          <momentIncrement>0.1</momentIncrement><thrustIncrement>0.2</thrustIncrement>
        </resultsData>
        """)


BEAM_RESULTS_XML = textwrap.dedent("""\
    <CandeDataBase>
      <Control><Heading>Test Beams</Heading></Control>
      <beamGroup><pipeCode>1</pipeCode><numBeamElem>2</numBeamElem><startBeamElem>1</startBeamElem><endBeamElem>2</endBeamElem><startNode>1</startNode><endNode>3</endNode></beamGroup>
      <beamResults><constIncrement>1</constIncrement>{s1r1}{s1r2}</beamResults>
      <beamResults><constIncrement>2</constIncrement>{s2r1}{s2r2}</beamResults>
    </CandeDataBase>
    """).format(
    s1r1=_beam_result(1, 1, with_extra=True),
    s1r2=_beam_result(2, 3, with_extra=True),
    s2r1=_beam_result(1, 1, with_extra=False),
    s2r2=_beam_result(2, 3, with_extra=False),
)


@pytest.fixture
def geom_file(tmp_path):
    p = tmp_path / "g_MeshGeom.xml"
    p.write_text(MESH_GEOM_XML)
    return p


@pytest.fixture
def results_file(tmp_path):
    p = tmp_path / "g_MeshResults.xml"
    p.write_text(MESH_RESULTS_XML)
    return p


@pytest.fixture
def beam_file(tmp_path):
    p = tmp_path / "g_BeamResults.xml"
    p.write_text(BEAM_RESULTS_XML)
    return p


@pytest.fixture
def geom(geom_file):
    return viz.parse_mesh_geom(geom_file)


@pytest.fixture
def results(results_file):
    return viz.parse_mesh_results(results_file)


@pytest.fixture
def beam(beam_file):
    return viz.parse_beam_results(beam_file)


# ── Parsers ───────────────────────────────────────────────────────────────────

class TestParsers:
    def test_parse_mesh_geom(self, geom):
        assert geom["heading"] == "Test Culvert Mesh"
        assert len(geom["nodes"]) == 5
        assert {e["type"] for e in geom["elements"]} == {"QUAD", "TRIA", "BEAM", "INTF"}
        assert len(geom["boundaries"]) == 3
        assert geom["boundaries"][0]["x_code"] == 1

    def test_parse_mesh_results(self, results):
        assert results["heading"] == "Test Results"
        assert len(results["steps"]) == 2
        assert results["steps"][0]["node_displacements"][0]["dx"] == 0.01
        assert results["steps"][0]["element_results"][0]["st4"] == 10.0

    def test_parse_beam_results(self, beam):
        assert beam["heading"] == "Test Beams"
        assert beam["beam_groups"][0]["num_elements"] == 2
        assert len(beam["steps"]) == 2
        r = beam["steps"][0]["results"][0]
        assert r["moment"] == 10.0
        assert r["result10"] == 15.0          # extra tags present
        assert beam["steps"][1]["results"][0]["result10"] == 0.0  # absent → default

    def test_parse_heading_missing(self, tmp_path):
        p = tmp_path / "h_MeshGeom.xml"
        p.write_text("<CandeDataBase><Control></Control></CandeDataBase>")
        assert viz.parse_mesh_geom(p)["heading"] == ""


# ── _require_plotly ─────────────────────────────────────────────────────────

class TestRequirePlotly:
    def test_returns_modules(self):
        go, sp = viz._require_plotly()
        assert hasattr(go, "Figure") and hasattr(sp, "make_subplots")

    def test_raises_without_plotly(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name.startswith("plotly"):
                raise ImportError("no plotly")
            return real_import(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(ImportError, match="plotly is required"):
            viz._require_plotly()


# ── Plot functions ────────────────────────────────────────────────────────────

class TestPlots:
    def test_plot_mesh_basic(self, geom):
        fig = viz.plot_mesh(geom)
        assert len(fig.data) > 0
        assert "Test Culvert Mesh" in fig.layout.title.text

    def test_plot_mesh_deformed_no_nodes_no_boundaries(self, geom, results):
        fig = viz.plot_mesh(geom, results=results, deformed=True, scale=5.0,
                            show_nodes=False, show_boundaries=False)
        assert "deformed" in fig.layout.title.text

    def test_plot_beam_results_known_and_unknown_quantity(self, beam):
        viz.plot_beam_results(beam, quantity="thrust")
        viz.plot_beam_results(beam, quantity="moment")
        fig = viz.plot_beam_results(beam, quantity="result10")
        assert fig.data
        # unknown quantity falls back to using the raw key as label
        fig2 = viz.plot_beam_results(beam, quantity="result14")
        assert "result14" in fig2.layout.yaxis.title.text

    def test_plot_beam_forces(self, beam):
        fig = viz.plot_beam_forces(beam)
        assert len(fig.data) == 3  # moment, thrust, shear

    def test_plot_displacement(self, geom, results):
        fig = viz.plot_displacement(geom, results)
        assert fig.data

    def test_plot_soil_stress_components(self, geom, results):
        viz.plot_soil_stress(geom, results, component="vertical")
        viz.plot_soil_stress(geom, results, component="shear_strain")
        # unknown component falls back to st4
        fig = viz.plot_soil_stress(geom, results, component="bogus")
        assert fig.data

    def test_plot_soil_stress_skips_element_with_missing_nodes(self):
        # QUAD whose nodes aren't in the geometry → no centroid, element skipped
        geom = {"heading": "x", "nodes": [], "elements": [
            {"id": 1, "n1": 90, "n2": 91, "n3": 92, "n4": 93,
             "mat": 1, "incr": 0, "type": "QUAD"}]}
        results = {"heading": "x", "steps": [{"step": 1, "node_displacements": [],
                   "element_results": [{"id": 1, "type": "QUAD", "st1": 0.0, "st2": 0.0,
                                        "st3": 0.0, "st4": 1.0, "st5": 0.0, "st6": 0.0}]}]}
        fig = viz.plot_soil_stress(geom, results)
        assert len(fig.data[0].x) == 0  # nothing plotted

    def test_plot_load_history_envelope_and_node(self, beam):
        env = viz.plot_load_history(beam, node=None, quantity="thrust")
        assert len(env.data) == 2  # max + min
        single = viz.plot_load_history(beam, node=1, quantity="moment")
        assert len(single.data) == 1

    def test_plot_load_history_unknown_quantity_label(self, beam):
        fig = viz.plot_load_history(beam, quantity="tang_pressure")
        assert "tang_pressure" in fig.layout.yaxis.title.text

    def test_plot_deformed_mesh(self, geom, results):
        fig = viz.plot_deformed_mesh(geom, results, scale=20.0)
        assert "Deformed" in fig.layout.title.text
