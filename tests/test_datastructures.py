# Unit tests for DataStructures
import pytest
import pandas as pd


from aiphoria.core.datastructures import (
    ObjectBase,
    Indicator,
    StockLifetimeOverride,
    Process,
    Flow,
    Stock,
    FlowModifier,
    ScenarioData,
    # ScenarioDefinition,
    Scenario,
    Color,
    ProcessEntry,
)


# **************
# * ObjectBase *
# **************
def test_objectbase_defaults():
    """
    Test creating ObjectBase-object
    """
    obj = ObjectBase()
    assert obj.id == -1
    assert obj.row_number == -1
    assert obj.is_virtual is False
    assert obj.is_valid is False


def test_objectbase_properties():
    """
    Test changing ObjectBase-object properties
    """
    obj = ObjectBase()
    obj.id = "abc"
    obj.row_number = 5
    obj.is_virtual = True

    assert obj.id == "abc"
    assert obj.row_number == 5
    assert obj.is_virtual is True


# *************
# * Indicator *
# *************
def test_indicator_creation():
    """
    Test creating Indicator-object
    """

    # Test __init__ / constructor
    name = "CO2"
    conversion_factor = 100.01
    comment = "Test comment"
    unit = "Mm3"

    ind = Indicator(name, conversion_factor, comment, unit)
    assert ind.name == name
    assert ind.conversion_factor == conversion_factor
    assert ind.comment == comment
    assert ind.unit == unit

    # Test setters/getters
    ind.name = "Test indicator name"
    assert ind.name == "Test indicator name"


# *************************
# * StockLifetimeOverride *
# *************************

def make_stock_lifetime_override_data():
    """
    Make test data for StockLifetimeOverride-object
    """
    return pd.Series([
        "P1", "20", "2005", "2010",
        "1.5", "2.0", "3.0", "Wet",
        "Test comment"])


def test_stock_lifetime_override_creation():
    """
    Test creating StockLifetimeOverride-object
    """
    data = make_stock_lifetime_override_data()
    slo = StockLifetimeOverride(data)
    slo.prepare_data()

    assert slo.process_id == "P1"

    assert isinstance(slo.lifetime, int)
    assert slo.lifetime == 20

    assert isinstance(slo.start_year, int)
    assert slo.start_year == 2005

    assert isinstance(slo.end_year, int)
    assert slo.end_year == 2010

    assert isinstance(slo.std_dev, float)
    assert slo.std_dev == 1.5

    assert isinstance(slo.std_dev, float)
    assert slo.shape == 2.0

    assert isinstance(slo.scale, float)
    assert slo.scale == 3.0

    # "Wet", "Dry", "Managed"
    assert slo.condition == "Wet"

    assert slo.comment == "Test comment"


# ***********
# * Process *
# ***********
def make_process_data() -> pd.Series:
    """
    Make test data for Process-object
    """
    return pd.Series([
        "P0", "loc", "P0:loc", "EOL", "10",
        "Stock lt source", "Fixed", "stddev=1.0, shape=1.0", 0.5, "WCS comment",
        1000, "Density source comment", "Modelling status", "Test comment", 1.0,
        2.0, "Label in graph"])


def test_process_creation():
    """
    Test creating Process-object
    """
    data = make_process_data()
    p = Process(data)
    assert p.name == "P0"
    assert p.location == "loc"
    assert p.id == "P0:loc"
    assert p.stock_lifetime == int(10)
    assert p.stock_lifetime_source == "Stock lt source"
    assert p.stock_distribution_type == "Fixed"
    assert p.stock_distribution_params == {"stddev": 1.0, "shape": 1.0}
    assert p.wood_content == 0.5
    assert p.wood_content_source == "WCS comment"
    assert p.density == 1000
    assert p.density_source == "Density source comment"
    assert p.modelling_status == "Modelling status"
    assert p.comment == "Test comment"
    assert p.position_x == 1.0
    assert p.position_y == 2.0
    assert p.label_in_graph == "Label in graph"


def test_process_is_valid():
    """
    Test Process-object valid state checking
    """
    data = make_process_data()
    p = Process(data)
    assert p.is_valid() is True

    p.name = None
    assert p.is_valid() is False


def test_process_parse_stock_lifetime_invalid():
    """
    Test parsing stock lifetime for Process-object
    """
    p = Process()

    # Expected: Raises Exception if unable to parse string to integer
    with pytest.raises(Exception):
        p._parse_stock_lifetime("Invalid lifetime", row_number=1)


def test_process_distribution_params_single():
    """
    Test parsing stock distribution parameters
    """
    p = Process()
    p._parse_and_set_distribution_params("alpha=2")
    assert isinstance(p.stock_distribution_params, dict)
    assert "alpha" in p.stock_distribution_params


def test_process_distribution_params_float():
    """
    Test parsing single value for stock distribution parameters
    """
    p = Process()
    p._parse_and_set_distribution_params("5.0")
    assert p.stock_distribution_params == 5.0


# ********
# * Flow *
# ********
def make_flow_data() -> pd.Series:
    """
    Make test data for Flow-object

    NOTE: Test data must be Series with index (= names as
    they appear in the settings file)
    """
    index = [
        "Source process",
        "Transformation stage",
        "Source process location",
        "Target process",
        "Transformation stage.1",
        "Target process location",
        "Source ID",
        "Target ID",
        "Value",
        "Unit",
        "Year",
        "Data source",
        "Data source comment",
        "CO2 (kg)",
        "Comment",
    ]

    s = pd.Series([
        "A", "stage", "loc",
        "B", "stage2", "loc2",
        "A_id", "B_id",
        100.0, "kg", 2020,
        "src", "comment",
        0.5, "Indicator comment",
    ], index=index)
    return s


def test_flow_creation():
    """
    Test creating Flow-object
    """
    data = make_flow_data()
    f = Flow(data)
    assert f.source_process == "A"
    assert f.target_process == "B"
    assert f.value == 100.0
    assert f.year == 2020


def test_flow_id_generation():
    """
    Test Flow-object ID generation
    """
    f = Flow(make_flow_data())
    assert f.id == "A_id B_id"


def test_flow_is_valid():
    """
    Test checking validity of Flow-object
    """
    f = Flow(make_flow_data())
    assert f.is_valid() is True

    f.value = None
    assert f.is_valid() is False


def test_flow_unit_absolute():
    """
    Test Flow-object absolute/relative state check
    """
    f = Flow(make_flow_data())
    assert f.is_unit_absolute_value is True

    f.unit = "%"
    assert f.is_unit_absolute_value is False


def test_flow_indicator_evaluation():
    """
    Test evaluating Flow-object indicator values.
    """
    f = Flow(make_flow_data())
    f.evaluated_value = 10
    f.evaluate_indicator_values_from_baseline_value()

    # Expect: Test data has one indicator so expect two elements
    vals = f.get_all_evaluated_values()
    assert len(vals) >= 1


def test_flow_invalid_indicator_columns():
    """
    Test checking Flow-object for invalid indicator columns
    """
    data = pd.concat([make_flow_data(), pd.Series(["extra"])])  # odd number
    # Expected: Raises Exception if length of indicator columns is odd
    with pytest.raises(Exception):
        Flow(data)


# *********
# * Stock *
# *********
def test_stock_basic():
    """
    Test Stock-object creation
    """
    p = Process(make_process_data())
    s = Stock(p)

    assert s.is_valid() is True
    assert s.stock_lifetime == p.stock_lifetime


def test_stock_lifetime_override():
    """
    Test stock lifetime override years
    """
    p = Process(make_process_data())
    s = Stock(p)

    slo = StockLifetimeOverride(make_stock_lifetime_override_data())
    slo.prepare_data()

    # Test that stock lifetime is overridden
    s.add_stock_lifetime_override(slo)
    lifetime, is_lifetime_override = s.get_lifetime_for_year(2005)
    assert is_lifetime_override is True
    assert lifetime == slo.lifetime

    # Test that stock lifetime is not overridden
    lifetime, is_lifetime_override = s.get_lifetime_for_year(2004)
    assert is_lifetime_override is False
    assert lifetime != slo.lifetime


def test_stock_default_lifetime():
    """
    Test Stock-object lifetime without StockLifetimeOverride
    """
    p = Process(make_process_data())
    s = Stock(p)

    lifetime, used = s.get_lifetime_for_year(1990)

    assert used is False
    assert lifetime == p.stock_lifetime


# ****************
# * FlowModifier *
# ****************
def make_flow_modifier_data():
    """
    Make test data for Flow-object
    """
    return pd.Series([
        "scenario", "A", "B",
        10.0, None, "Value",
        2000, 2005, "linear", True,
        "C"
    ])


def test_flow_modifier_basic():
    """
    Test FlowModifier-object creation

    """
    fm = FlowModifier(make_flow_modifier_data())

    assert fm.scenario_name == "scenario"
    assert fm.use_change_in_value is True
    assert fm.has_target is True


def test_flow_modifier_year_range():
    """
    Test FlowModifier-object year range
    """
    fm = FlowModifier(make_flow_modifier_data())
    years = fm.get_year_range()

    assert years == [2000, 2001, 2002, 2003, 2004, 2005]


def test_flow_modifier_opposite_targets():
    """
    Test FlowModifier-object opposite target flows
    """
    fm = FlowModifier(make_flow_modifier_data())
    ids = fm.get_opposite_target_flow_ids()

    assert len(ids) == 1
    assert "A C" in ids[0]


# ****************
# * ScenarioData *
# ****************
def test_scenario_data_defaults():
    """
    Test ScenarioData-object creation with default values
    """
    sd = ScenarioData()

    assert sd.years == []
    assert sd.start_year == 0
    assert sd.end_year == 0


def test_scenario_data_year_bounds():
    """
    Test ScenarioData-object years
    NOTE: ScenarioData does not fill the gaps in years
    """
    sd = ScenarioData(years=[2000, 2005, 2010])

    assert sd.start_year == 2000
    assert 2006 not in sd.years
    assert sd.end_year == 2010


# ************
# * Scenario *
# ************
def test_scenario_copy():
    """
    Test ScenarioData-object functionality of copying
    data from baseline years to scenarios
    """
    sd = ScenarioData(years=[2000])
    scenario = Scenario()

    scenario.copy_from_baseline_scenario_data(sd)

    assert scenario.scenario_data is not sd
    assert scenario.scenario_data.years == sd.years


# *********
# * Color *
# *********
def test_color_from_list():
    """
    Test Color-object creation
    """
    c = Color(["red", "#FF0000"])

    assert c.name == "red"
    assert str(c) == "#ff0000"


def test_color_rgb_conversion():
    """
    Test Color-object color conversion from hex string to RGB values (float)
    """
    c = Color(["red", "#FF0000"])

    assert c.get_red_as_float() == 1.0
    assert c.get_green_as_float() == 0.0
    assert c.get_blue_as_float() == 0.0


# ****************
# * ProcessEntry *
# ****************
def test_process_entry_flows():
    """
    Test ProcessEntry-object
    """
    p = Process(make_process_data())
    pe = ProcessEntry(p)

    f = Flow(make_flow_data())

    pe.add_inflow(f)
    pe.add_outflow(f)

    assert len(pe.inflows) == 1
    assert len(pe.outflows) == 1


def test_process_entry_remove():
    """
    Test ProcessEntry-object functionality when adding and removing flows
    """
    p = Process(make_process_data())
    pe = ProcessEntry(p)

    f = Flow(make_flow_data())
    pe.add_inflow(f)

    pe.remove_inflow(f.id)

    assert len(pe.inflows) == 0

    with pytest.raises(Exception):
        pe.remove_inflow("nonexistent")