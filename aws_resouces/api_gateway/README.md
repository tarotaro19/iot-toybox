# API Gatewayの設定

|method|endpoint|action|
| ---- | ---- | ---- |
|POST|/toybox/{deviceId}/control|lambda:toybox-control|
|PUT|/toybox/{deviceId}/properties/operationMode|lambda:toybox-operationMode-handler|
|GET|/toybox/{deviceId}/shadow|lambda:toybox-shadow-bridge|
|GET, POST|/toybox/{deviceId}/toys|lambda:toybox-api-handler|
