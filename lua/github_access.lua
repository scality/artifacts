--
--
-- Verify throw basic auth, the user is in the github company
--
--
local github_api_enabled = os.getenv('GITHUB_API_ENABLED')
local github_api_company = os.getenv('GITHUB_API_COMPANY')

function wrong_credentials()
   ngx.header.content_type = 'text/plain'
   ngx.header['WWW-Authenticate'] = 'Basic realm="Access to the Scality Artifacts", charset="UTF-8"'
   ngx.status = ngx.HTTP_UNAUTHORIZED
   ngx.log(ngx.STDERR, '401 Access Denied')
   return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end


function not_allowed()
   ngx.header.content_type = 'text/plain'
   ngx.status = ngx.HTTP_FORBIDDEN
   ngx.log(ngx.STDERR, '403 Forbidden response')
   return ngx.exit(ngx.HTTP_FORBIDDEN)
end

function authenticate(auth)
    divider = auth:find(':')
    local username = auth:sub(0, divider-1)
    local resp = {}

    local res =  ngx.location.capture("/force_github_request/orgs/" .. github_api_company .. "/members/" .. username)
    ngx.log(ngx.STDERR, "status member \t\t" .. res.status)

    if res.status ~= 204 then
        return  false
    end
    return true
end

function verify_header()
    -- Test Authentication header is set and with a value
    local header = ngx.req.get_headers()['Authorization']
    if header == nil or header:find(" ") == nil then
        return false
    end

    local divider = header:find(' ')
    if header:sub(0, divider-1) ~= 'Basic' then
        return false
    end

    local auth = ngx.decode_base64(header:sub(divider+1))
    if auth == nil or auth:find(':') == nil then
        return false
    end
    return auth
end

auth = verify_header()
if not auth then
    return wrong_credentials()
end

local user = authenticate(auth)
ngx.log(ngx.STDERR, user)
if not user then
    return not_allowed()
end
