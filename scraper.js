var casper = require('casper').create({
  verbose: true,
  logLevel: 'error',
  clientScripts:  [
    'includes/jquery.js',      // These two scripts will be injected in remote
    'includes/underscore.js'   // DOM on every request
  ], 
});

// removing default options passed by the Python executable
casper.cli.drop("cli");
casper.cli.drop("casper-path");

if ((casper.cli.args.length < 2).length === 0) {
    casper.echo("Usage: casperjs scraper.js <controller-url> <json-out-file>").exit(1);
}

var SEARCH_URL = casper.cli.args[0];
var FILENAME = casper.cli.args[1];

var fs = require("fs");
var _ = require("proxies/underscore");

var aircrafts;

casper.start(SEARCH_URL);

casper.waitForSelector('#footer_copyright');

casper.then(function() {
  this.evaluate(function() {

    _.extend(window, {

      getAircraftSpecs: function(el) {
        var specsString = $(el).find('td.med > span.listings-label:nth-child(1)').parent().clone().children().replaceWith('\n').end().text().trim();
        if (specsString.length === 0) {
          return null;
        }
        specsString = specsString.replace(/\n\n\s*/g, '\n');
        return _.object(["sn", "reg", "tt", "pax"], specsString.split('\n'));
      },

      getTitleInfo: function(el) {
        var $el = $(el).find("#aDetailsLink");
        return {
          link: 'http://www.controller.com' + $el.attr('href'),
          title: $el.text(),
        };
      },

      getPrice: function(el) {
        return $(el).find("#auction-CNTprice").text();  
      },

      getDescription: function(el) {
        return $(el).find(".listing-summary tr:nth-child(1) span").text().trim();
      },

      getBrokerInfo: function(el) {
        var $cell = $(el).find("td.comp-info"),
            cellText = $cell.text().trim();
            infoArr = _.map(cellText.replace(/\n+/g, '\n').split("\n"), function(l) { return l.trim(); }),
            infoObj = _.object(["brokerName", "location", "phone", "phone2"], infoArr);

        infoObj["phone"] = infoObj["phone"].replace(/Phone:\s+/, '');
        infoObj["phone2"] = infoObj["phone2"].replace(/or\s+/, '');

        return _.extend({
          brokerURL: $cell.find("> a").attr("href"),
        }, infoObj);
      },

      getThumbnailURL: function(el) {
        return $(el).find("td.photo img").attr("src");
      },

      getUpdatedAt: function(el) {
        return $(el).find("span.date-time3").text().replace("Updated:", "").trim();
      },

    });

  });
});

casper.then(function(){
  aircrafts = this.evaluate(function() {
    var rows = $('.listings > tbody > tr > td.photo').parents(".listings tr")

    return $.map(rows, function(el, i){
      
      return _.extend({
        price: getPrice(el),
        desc: getDescription(el),
        thumb: getThumbnailURL(el),
        updatedAt: getUpdatedAt(el),
      },
      getTitleInfo(el),
      getAircraftSpecs(el),
      getBrokerInfo(el));

    });

  });
});

casper.run(function(){
  fs.write(FILENAME, JSON.stringify(aircrafts));
  this.exit();
});

