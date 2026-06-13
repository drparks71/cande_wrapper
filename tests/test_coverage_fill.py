"""Coverage fill-ins: engine helpers/Windows shim, package lazy loader,
vehicle equality guards, and pipe thickness-lookup branches.
"""
import sys
import types
from pathlib import Path

import pytest

import cande_wrapper
from cande_wrapper.engine import CandeEngine, CandeResult, _find_gfortran_dirs
from cande_wrapper import pipes as P
from cande_wrapper.vehicle import Axle, Vehicle, WheelFootprint


# ── package lazy loader (__init__.__getattr__) ───────────────────────────────

def test_lazy_loads_visualization_symbol():
    fn = cande_wrapper.plot_mesh
    assert callable(fn)


def test_unknown_attribute_raises():
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = cande_wrapper.does_not_exist


# ── _find_gfortran_dirs ───────────────────────────────────────────────────────

class TestFindGfortranDirs:
    def test_returns_list(self):
        assert isinstance(_find_gfortran_dirs(), list)

    def test_includes_gfortran_bin_and_conda(self, monkeypatch, tmp_path):
        import shutil
        fake_bin = tmp_path / "bin" / "gfortran"
        fake_bin.parent.mkdir(parents=True)
        fake_bin.touch()
        monkeypatch.setattr(shutil, "which", lambda name: str(fake_bin))

        conda = tmp_path / "conda"
        (conda / "Library" / "bin").mkdir(parents=True)
        monkeypatch.setenv("CONDA_PREFIX", str(conda))

        dirs = _find_gfortran_dirs()
        assert str(fake_bin.parent) in dirs
        assert str(conda / "Library" / "bin") in dirs

    def test_windows_candidate_dir(self, monkeypatch):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda name: None)
        monkeypatch.delenv("CONDA_PREFIX", raising=False)
        # make the Strawberry/msys candidate paths look present
        real_is_dir = Path.is_dir
        monkeypatch.setattr(Path, "is_dir",
                            lambda self: "Strawberry" in str(self) or "mingw64" in str(self))
        dirs = _find_gfortran_dirs()
        assert any("mingw64" in d or "Strawberry" in d for d in dirs)


# ── Windows DLL-load shim in CandeEngine.run ──────────────────────────────────

class TestWindowsDllShim:
    def _bad_cande(self):
        # a module that lacks run_cande → `from ... import run_cande` raises ImportError
        return types.ModuleType("cande_wrapper._cande")

    def _good_cande(self):
        m = types.ModuleType("cande_wrapper._cande")
        m.run_cande = lambda prefix: 0
        return m

    def test_nt_recovers_after_adding_dll_dir(self, tmp_workdir, monkeypatch):
        # build the engine before patching os.name (pathlib keys off os.name)
        engine = CandeEngine(work_dir=tmp_workdir)
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.setitem(sys.modules, "cande_wrapper._cande", self._bad_cande())
        monkeypatch.setattr("cande_wrapper.engine._find_gfortran_dirs",
                            lambda: ["C:\\fake\\bin"])

        def add_dll(_dir):
            # simulate the runtime DLLs becoming loadable
            sys.modules["cande_wrapper._cande"] = self._good_cande()

        monkeypatch.setattr("os.add_dll_directory", add_dll, raising=False)
        result = engine.run("MGK-IO")
        assert isinstance(result, CandeResult)

    def test_nt_second_import_failure_raises(self, tmp_workdir, monkeypatch):
        engine = CandeEngine(work_dir=tmp_workdir)
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.setitem(sys.modules, "cande_wrapper._cande", self._bad_cande())
        monkeypatch.setattr("cande_wrapper.engine._find_gfortran_dirs", lambda: [])
        monkeypatch.setattr("os.add_dll_directory", lambda d: None, raising=False)
        with pytest.raises(ImportError, match="DLL load failed"):
            engine.run("MGK-IO")


# ── CandeResult plot delegators ───────────────────────────────────────────────

# minimal XML good enough for the parsers used by the delegators
_GEOM = ("<CandeDataBase><Control><Heading>h</Heading></Control>"
         "<nodeCoord><nodeNumber>1</nodeNumber><nodeXCoord>0</nodeXCoord><nodeYCoord>0</nodeYCoord></nodeCoord>"
         "<nodeCoord><nodeNumber>2</nodeNumber><nodeXCoord>1</nodeXCoord><nodeYCoord>0</nodeYCoord></nodeCoord>"
         "<elemConn><elemNumber>1</elemNumber><elemNode1>1</elemNode1><elemNode2>2</elemNode2>"
         "<elemNode3>2</elemNode3><elemNode4>2</elemNode4><elemMatNum>1</elemMatNum>"
         "<elemConstrIncr>0</elemConstrIncr><elemType>BEAM</elemType></elemConn></CandeDataBase>")

_BEAM = ("<CandeDataBase><Control><Heading>h</Heading></Control>"
         "<beamResults><constIncrement>1</constIncrement><resultsData>"
         "<resultId>1</resultId><nodeNumber>1</nodeNumber><elementNumber>1</elementNumber>"
         "<beamGroupNumber>1</beamGroupNumber><pipeType>1</pipeType><xCoord>0</xCoord><yCoord>0</yCoord>"
         "<xDisp>0</xDisp><yDisp>0</yDisp><bendingMoment>1</bendingMoment><thrustForce>2</thrustForce>"
         "<shearForce>3</shearForce><normalPressure>0</normalPressure><tangPressure>0</tangPressure>"
         "<momentIncrement>0</momentIncrement><thrustIncrement>0</thrustIncrement>"
         "</resultsData></beamResults></CandeDataBase>")


def test_candresult_plot_delegators(tmp_path):
    (tmp_path / "p_MeshGeom.xml").write_text(_GEOM)
    (tmp_path / "p_BeamResults.xml").write_text(_BEAM)
    result = CandeResult(tmp_path, "p")
    assert result.plot_mesh().data
    assert result.plot_beam_forces().data
    assert "p" in repr(result)


# ── vehicle __eq__ type guards ────────────────────────────────────────────────

def test_vehicle_equality_type_guards():
    wf = WheelFootprint(length=10, width=20)
    assert (wf == "not a footprint") is False
    assert (wf == WheelFootprint(length=10, width=20)) is True

    ax = Axle(weight=16000, spacing=6)
    assert (ax == 123) is False
    assert (ax == Axle(weight=16000, spacing=6)) is True

    v = Vehicle(name="HS20", footprint=wf, axles=[ax])
    assert (v == object()) is False
    assert (v == Vehicle(name="HS20", footprint=wf, axles=[ax])) is True


# ── pipe validation + thickness-lookup elif chains ────────────────────────────

class TestPipeValidationAndLookups:
    def test_material_only_reprs(self):
        # PVC/HDPE/Aluminum are material models (no diameter)
        assert "CorrugatedPVC" in repr(P.CorrugatedPVC())
        assert "CorrugatedHDPE" in repr(P.CorrugatedHDPE())
        assert "CorrugatedAluminum" in repr(P.CorrugatedAluminum())

    def test_smooth_hdpe_repr_and_validation(self):
        assert "SmoothHDPE" in repr(P.SmoothHDPE(diameter=12, wall_thickness=0.5))
        with pytest.raises(ValueError):
            P.SmoothHDPE(diameter=-1, wall_thickness=0.5)
        with pytest.raises(ValueError):
            P.SmoothHDPE(diameter=12, wall_thickness=0)

    def test_precast_concrete_validation(self):
        with pytest.raises(ValueError):
            P.PrecastConcrete(diameter=-1, wall_thickness=5.0)

    def test_ductile_iron_repr_and_validation(self):
        assert "DuctileIron" in repr(P.DuctileIron(diameter=24, wall_thickness=0.33))
        with pytest.raises(ValueError):
            P.DuctileIron(diameter=-1, wall_thickness=0.33)
        with pytest.raises(ValueError):
            P.DuctileIron(diameter=24, wall_thickness=0)

    def test_precast_elastic_modulus(self):
        p = P.PrecastConcrete(diameter=48, wall_thickness=5.0)
        assert p.elastic_modulus > 0

    @pytest.mark.parametrize("dia", [12, 24, 36, 48, 60, 72, 96, 120])
    def test_astm_c76_thickness_branches(self, dia):
        p = P.PrecastConcrete.astm_c76_class_iii(diameter=dia)
        assert p.wall_thickness > 0
        assert p.diameter == dia

    @pytest.mark.parametrize("dia", [4, 6, 8, 10, 12, 16, 20, 24, 30, 36, 42, 48, 60])
    def test_awwa_c151_thickness_branches(self, dia):
        p = P.DuctileIron.awwa_c151(diameter=dia)
        assert p.wall_thickness > 0
        assert p.diameter == dia
