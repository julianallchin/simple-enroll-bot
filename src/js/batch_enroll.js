var done = arguments[0];
SE_NetworkEndpoint.executeRequest("SE_BATCHENROLL", "<Career>" + "UG" + "</Career>", function (soap_response, status) {
  var s = new XMLSerializer();
  done(s.serializeToString(soap_response));
});
