--
--
-- Verify throw basic auth, the user is in the github company
--
--
local github_api_enabled            = os.getenv('GITHUB_API_ENABLED')
local github_api_company            = os.getenv('GITHUB_API_COMPANY')
local env_github_restriction_upload = os.getenv('GITHUB_USER_ALLOWED_UPLOAD')
local github_auth_cache_dir         = "/data/nginx/artifacts_github_auth_cache"
local github_restriction_users = {}
local github_restriction_paths = { "/upload/", "/copy/" }

-- Set default values if needed
--
if github_api_enabled == nil then
    github_api_enabled = "true"
end
if github_api_company == nil then
    github_api_company = "scality"
end

-- Feed github_restriction_users if neeeded
--
if env_github_restriction_upload ~= nil then
    for allowed_user in env_github_restriction_upload:gmatch("([^,]+)") do
        table.insert(github_restriction_users, allowed_user)
    end
end

function wrong_credentials()
   ngx.header.content_type = 'text/plain'
   ngx.header['WWW-Authenticate'] = 'Basic realm="Access to the Scality Artifacts", charset="UTF-8"'
   ngx.status = ngx.HTTP_UNAUTHORIZED
   return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

function not_allowed()
   ngx.header.content_type = 'text/plain'
   ngx.status = ngx.HTTP_FORBIDDEN
   return ngx.exit(ngx.HTTP_FORBIDDEN)
end

function read_cache(auth_md5)
    local path = github_auth_cache_dir .. "/" .. auth_md5

    local file = io.open(path, "rb")
    if not file then
        return nil
    end

    local content = file:read("*a")
    file:close()

    return content
end

function update_cache(auth_md5, status)
    local path = github_auth_cache_dir .. "/" .. auth_md5

    local cmd = io.popen("mktemp -p " .. github_auth_cache_dir .. " tmp_XXXXXXXXX")
    local path_orig = cmd:read()
    cmd:close()

    if path_orig == nil then
        return nil
    end

    local file = io.open(path_orig, "wb")
    if not file then
        return nil
    end

    file:write(status)
    file:close()

    local res = os.rename(path_orig, path)
    if res == nil then
        os.remove(path_orig)
        return nil
    end
end

function authenticate(auth)
    local divider = auth:find(':')
    local username = auth:sub(0, divider-1)
    local auth_md5 = ngx.md5(auth)

    local cached_status = read_cache(auth_md5)

    if cached_status == nil then
        local res =  ngx.location.capture("/force_github_request/orgs/" .. github_api_company .. "/members/" .. username)

        update_cache(auth_md5, res.status)

        if res.status ~= 204 then
            ngx.log(ngx.STDERR, 'User ' .. username .. ' not allowed (github auth cache MISS)')
            return  false
        end
        return true
    else
        if cached_status ~= '204' then
            ngx.log(ngx.STDERR, 'User ' .. username .. ' not allowed (github auth cache HIT)')
	    return false
        end
        return true
    end
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

function restriction_check(auth)
    local divider = auth:find(':')
    local username = auth:sub(0, divider-1)
    local location = nil

    for _,v in pairs(github_restriction_paths) do
        if string.sub(ngx.var.request_uri, 1,string.len(v)) == v then
            location = v
            break
        end
    end

    if location == nil then
        return true
    end

    for _,v in pairs(github_restriction_users) do
        if v == username then
            return true
        end
    end

    ngx.log(ngx.STDERR, 'User ' .. username .. ' not allowed for restricted access to ' .. location)
    return false
end

if github_api_enabled == 'true' and ngx.var.remote_addr ~= '127.0.0.1' then
    local auth = verify_header()
    if not auth then
        return wrong_credentials()
    end

    local user = authenticate(auth)
    if not user then
        return not_allowed()
    end

    if not restriction_check(auth) then
        return not_allowed()
    end
end
