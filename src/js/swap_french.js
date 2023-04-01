const req = '<Career>UG</Career><CourseID></CourseID><ClassNumber>9310</ClassNumber><GradingBasis>RLT</GradingBasis><Units>5</Units><WaitList>N</WaitList><DropifEnroll>0</DropifEnroll><PermissionNbr>0</PermissionNbr><AssociatedClass1 Nbr="0" Taken="" ClassType="" ClassSection=""/><AssociatedClass2 Nbr="0" Taken="" ClassType="" ClassSection=""/><SwapWithClassNbr>15126</SwapWithClassNbr>';

var done = arguments[0];
SE_NetworkEndpoint.executeRequest("SE_EXECUTE_ENROLL", req, function (soap_response, status) {
  var s = new XMLSerializer();
  done(s.serializeToString(soap_response));
});
