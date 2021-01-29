import json
import toys_handler

def lambda_handler(event, context):
    print(event)
    resource_path =  event['resource']
    path_paremeters = event['pathParameters']
    method = event['httpMethod']
    try:
        request_body = json.loads(event['body'])
    except:
        request_body = None
    ret = {'statusCode': 400, 'body': json.dumps('request is invalid')}
    
    if resource_path == '/grouph-toybox/{deviceId}/toys':
        ret = toys_handler.handler(resource_path, path_paremeters, method, request_body)
    
    return ret
