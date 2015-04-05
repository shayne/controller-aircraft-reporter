import copy
import json
import unittest

from run import AircraftData, AircraftReporter


class TestBaseClass(unittest.TestCase):
    def setUp(self):
        self.fixture_file = file("fixture.json")
        self.json_obj = json.load(self.fixture_file)
        self.aircraft_data = AircraftData(self.json_obj)

    def tearDown(self):
        self.fixture_file.close()
        self.json_obj = None
        self.aircraft_data = None


class TestAircraftDataClass(TestBaseClass):
    def setUp(self):
        super(TestAircraftDataClass, self).setUp()

    def test_subscripting(self):
        reg = self.aircraft_data.get_reg(0)
        self.assertEquals(self.aircraft_data[reg]["reg"], self.aircraft_data.get_reg(0))

    def test_arithmetic(self):
        self.assertEquals(set(), self.aircraft_data - self.aircraft_data)

    def test_aircraft_removed(self):
        json_obj2 = self.json_obj[1:]
        new_aircraft = AircraftData(json_obj2)
        old_aircraft = self.aircraft_data

        self.assertEquals(new_aircraft - old_aircraft, set([]))
        self.assertEquals(old_aircraft - new_aircraft, set([self.aircraft_data.get_reg(0)]))

    def test_aircraft_added(self):
        json_obj2 = self.json_obj[1:]
        old_aircraft = AircraftData(json_obj2)
        new_aircraft = self.aircraft_data

        self.assertEquals(old_aircraft - new_aircraft, set([]))
        self.assertEquals(new_aircraft - old_aircraft, set([self.aircraft_data.get_reg(0)]))

    def test_iteration(self):
        self.assertItemsEqual([x for x in self.aircraft_data], [x["reg"] for x in self.json_obj])


class TestAircraftReporter(TestBaseClass):

    def setUp(self):
        super(TestAircraftReporter, self).setUp()
        self.new_aircraft = self.aircraft_data
        self.old_aircraft = AircraftData(copy.deepcopy(self.json_obj))

    def test_aircraft_added(self):
        del self.old_aircraft[self.old_aircraft.get_reg(0)]
        reporter = AircraftReporter(self.new_aircraft, self.old_aircraft)
        reporter.report()

        self.assertEqual(1, len(reporter._new_aircraft))

    def test_aircraft_removed(self):
        del self.new_aircraft[self.new_aircraft.get_reg(0)]
        reporter = AircraftReporter(self.new_aircraft, self.old_aircraft)
        reporter.report()

        self.assertEqual(1, len(reporter._removed_aircraft))

    def test_aircraft_price_changed(self):
        self.new_aircraft[self.new_aircraft.get_reg(0)]["price"] = "US $123,456"
        reporter = AircraftReporter(self.new_aircraft, self.old_aircraft)
        reporter.report()

        self.assertEqual(1, len(reporter._new_price_aircraft))

    def test_aircraft_updated(self):
        self.new_aircraft[self.new_aircraft.get_reg(0)]["updatedAt"] = "1/1/2014 12:00:00"
        reporter = AircraftReporter(self.new_aircraft, self.old_aircraft)
        reporter.report()

        self.assertEqual(1, len(reporter._updated_aircraft))

    def test_multi_change(self):
        self.new_aircraft[self.new_aircraft.get_reg(0)]["updatedAt"] = "1/1/2014 12:00:00"
        self.new_aircraft[self.new_aircraft.get_reg(1)]["price"] = "US $123,456"
        reg2 = self.old_aircraft.get_reg(2)
        del self.old_aircraft[reg2]
        reg3 = self.new_aircraft.get_reg(3)
        del self.new_aircraft[reg3]

        reporter = AircraftReporter(self.new_aircraft, self.old_aircraft)
        reporter.report()

        self.assertEquals(reporter._updated_aircraft[0]["reg"], self.new_aircraft.get_reg(0))
        self.assertEquals(reporter._new_price_aircraft[0]["reg"], self.new_aircraft.get_reg(1))
        self.assertEquals(reporter._new_aircraft[0]["reg"], reg2)
        self.assertEquals(reporter._removed_aircraft[0]["reg"], reg3)


if __name__ == "__main__":
    unittest.main()
