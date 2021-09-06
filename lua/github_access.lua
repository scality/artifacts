--
--
-- Verify throw basic auth, the user is in the github company
--
--
local github_api_enabled            = os.getenv('GITHUB_API_ENABLED')
local github_api_company            = os.getenv('GITHUB_API_COMPANY')
local env_github_restriction_upload = os.getenv('GITHUB_USER_ALLOWED_UPLOAD')
local github_auth_cache_dir         = "/data/nginx/artifacts_github_auth_cache"
local github_restriction_upload = {}

for allowed_user in env_github_restriction_upload:gmatch("([^,]+)") do
    table.insert(github_restriction_upload, allowed_user)
    ngx.log(ngx.STDERR, allowed_user)
end

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
    path_orig = cmd:read()
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

    res = os.rename(path_orig, path)
    if res == nil then
        os.remove(path_orig)
        return nil
    end
end

function authenticate(auth)
    divider = auth:find(':')
    local username = auth:sub(0, divider-1)
    local auth_md5 = ngx.md5(auth)

    cached_status = read_cache(auth_md5)

    if cached_status == nil then
        local res =  ngx.location.capture("/force_github_request/orgs/" .. github_api_company .. "/members/" .. username)
        ngx.log(ngx.STDERR, "status member \t\t" .. res.status)

        update_cache(auth_md5, res.status)

        if res.status ~= 204 then
            return  false
        end
        return true
    else
        if cached_status ~= '204' then
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

function upload_checks()
    ngx.log(ngx.STDERR, "upload check url is called ")
    if string.sub(ngx.var.request_uri, 1,string.len("/upload/")) ~= "/upload/" then
        return true
    end
    local res =  ngx.location.capture("/force_github_request/user")

    username = res.body:match('"login": "([^/"]*)')
    ngx.log(ngx.STDERR, username)
    for _,v in pairs(github_restriction_upload) do
        if v == username  then
            return true
        end
    end
    ngx.log(ngx.STDERR, 'User ' .. username .. 'not allowed to upload image')
    return false
end

if github_api_enabled == 'true' then
    auth = verify_header()
    if not auth then
        return wrong_credentials()
    end

    local user = authenticate(auth)
    ngx.log(ngx.STDERR, user)
    if not user then
        return not_allowed()
    end
end
