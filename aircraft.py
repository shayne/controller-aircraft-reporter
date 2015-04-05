#!/usr/bin/env python
import json
import os
import smtplib
import subprocess
import sys
import tempfile


CWD = os.path.dirname(os.path.realpath(__file__))
os.chdir(CWD)

OLD_AIRCRAFT_FILENAME = "old_aircraft.json"


class AircraftScraper(object):
    @classmethod
    def scrape(cls):
        with tempfile.NamedTemporaryFile(delete=True) as out_file:
            return cls().run(out_file)

    def __init__(self):
        self.js_filename = os.path.join(CWD, "scraper.js")

    def run(self, out_file):
        cmd = self.construct_command(out_file.name)
        subprocess.check_call(cmd, shell=True, env=os.environ)
        entries = json.load(out_file)
        data = AircraftData(entries)
        return data

    def construct_command(self, out_filename):
        return 'casperjs "%s" "%s" "%s"' % (self.js_filename, os.environ["CONTROLLER_SEARCH_URL"], out_filename)


class AircraftArchiver(object):
    @classmethod
    def unarchive(cls):
        with file(OLD_AIRCRAFT_FILENAME) as fp:
            return AircraftData(json.load(fp))

    @classmethod
    def archive(cls, aircraft_data):
        with file(OLD_AIRCRAFT_FILENAME, "w+") as fp:
            json.dump(aircraft_data.json_obj, fp)
        

class AircraftData(object):
    def __init__(self, json_obj):
        self.json_obj = json_obj
        self.index = {}
        self.reg_set = None
        self.build_index()

    def build_index(self):
        for x in self.json_obj:
            self[x["reg"]] = x 
        self.reg_set = set(self.index.keys())

    def get_reg(self, idx):
        return self[self.json_obj[idx]["reg"]]["reg"]

    def __getitem__(self, key):
        return self.index[key]
    
    def __setitem__(self, key, val):
        self.index[key] = val

    def __delitem__(self, key):
        self.reg_set.remove(key)
        del self.index[key]

    def __sub__(a, b):
        return a.reg_set - b.reg_set
    
    def __iter__(self):
        return self.index.__iter__()


class AircraftReporter(object):
    def __init__(self, new_data, old_data):
        self.new = new_data
        self.old = old_data
        self._new_aircraft = []
        self._removed_aircraft = []
        self._new_price_aircraft = []
        self._updated_aircraft = []

    def report(self):
        self._record_changes()
        if not (self._new_aircraft or self._new_price_aircraft or self._removed_aircraft or self._updated_aircraft):
            return
        return {"new": self._new_aircraft,
                "price": self._new_price_aircraft,
                "removed": self._removed_aircraft,
                "updated": self._updated_aircraft
                }

    def _record_changes(self):
        new_price_regs = []
        regs_updated = []
        
        for reg in [r for r in self.new if self.old.index.has_key(r)]:
            new_ac = self.new[reg]
            old_ac = self.old[reg]
 
            if new_ac["price"] != old_ac["price"]:
                self._new_price_aircraft.append(self.new[reg])
            elif new_ac["updatedAt"] and new_ac["updatedAt"] != old_ac["updatedAt"]:
                self._updated_aircraft.append(self.new[reg])
    
        regs_added = self.new - self.old
        regs_removed = self.old - self.new
        
        if regs_added:
            [self._new_aircraft.append(self.new[r]) for r in regs_added]

        if regs_removed:
            [self._removed_aircraft.append(self.old[r]) for r in regs_removed]


class AircraftDelivery(object):
    to_addrs = os.environ["TO_ADDRS"]
    from_addr = os.environ["FROM_ADDR"]

    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]

    def __init__(self, report):
        self.report = report

    def send(self):
        msg = """MIME-Version: 1.0
Content-type: text/html
Subject: %s

""" % os.environ["EMAIL_SUBJECT"]

        msg += self._build_section("New Aircraft", self.report["new"])
        msg += self._build_section("Price Change", self.report["price"])
        msg += self._build_section("Updated", self.report["updated"])
        msg += self._build_section("removed", self.report["removed"])

        # The actual mail send
        server = smtplib.SMTP(os.environ["SMTP_HOST"])
        server.starttls()
        server.login(self.username, self.password)
        server.sendmail(self.from_addr, self.to_addrs, msg)
        server.quit()

    def _build_section(self, title, aircraft):
        msg = ""
        if aircraft:
            msg += "<h1>%s</h1>" % title
            msg += "<table>"
            for x in aircraft:
                msg += self._build_aircraft_row(x)
            msg += "</table>"
        return msg

    def _build_aircraft_row(self, aircraft):
        msg = "<tr>"
        msg += '<td><img src="%s" /></td>' % aircraft["thumb"]
        msg += "<td>"
        msg += '<a href="%(link)s">%(title)s</a> - <b>%(price)s</b><br /> %(desc)s' % {
                    "link": aircraft["link"],
                    "title": aircraft["title"],
                    "price": aircraft["price"],
                    "desc": aircraft["desc"]
                }
        msg += "</td><td><dl>"
        msg += '<dt>Serial #:</dt><dd>%s</dd>' % aircraft["sn"]
        msg += '<dt>Tail #:</dt><dd>%s</dd>' % aircraft["reg"]
        msg += '<dt>Total Time:</dt><dd>%s</dd>' % aircraft.get("tt", "???")
        msg += "</dl></td></tr>"
        return msg


def main():
    new_aircraft = AircraftScraper.scrape()
    old_aircraft = AircraftArchiver.unarchive()
    report = AircraftReporter(new_aircraft, old_aircraft).report()
    if report:
        print "Sending report", report
        AircraftDelivery(report).send()
    AircraftArchiver.archive(new_aircraft)


if __name__ == "__main__":
    sys.exit(main())

