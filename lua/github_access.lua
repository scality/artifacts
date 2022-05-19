--
--
-- Verify throw basic auth, the user is in the github company
--
--
local github_api_enabled            = os.getenv('GITHUB_API_ENABLED')
local github_api_company            = os.getenv('GITHUB_API_COMPANY')
local env_github_restriction_upload = os.getenv('GITHUB_USER_ALLOWED_UPLOAD')
local github_auth_cache_dir         = "/data/nginx/artifacts_github_auth_cache"
local github_restriction_users      = {}
local github_restriction_paths      = { "/upload/", "/copy/", "/add_metadata/" }
local bot_username                  = os.getenv('BOT_USERNAME')
local bot_token                     = os.getenv('BOT_TOKEN')
local local_bot_creds_enabled       = false

local error_message = '<br/><h2>You are not allowed to connect to artifacts, for more information on how to connect, check the <a href=https://github.com/scality/action-docs/blob/main/artifacts.md>documentation</a><h2>'

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

-- Detect if we have to use local bot creds
--
if bot_username ~= nil and bot_username ~= "" and bot_token ~= nil and bot_token ~= "" then
    local_bot_creds_enabled = true
end

function wrong_credentials()
   ngx.header.content_type = 'text/plain'
   ngx.header['WWW-Authenticate'] = 'Basic realm="Access to the Scality Artifacts", charset="UTF-8"'
   ngx.status = ngx.HTTP_UNAUTHORIZED
	 ngx.header["Content-Type"] =  "text/html"
	 ngx.say('<html><head><title>401 Not Authorized</title></head><body><center><h1>401 Not Authorized</h1></center><hr><center>nginx'.. error_message .. '</center></body><html>')
   return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

function not_allowed()
   ngx.header.content_type = 'text/plain'
   ngx.status = ngx.HTTP_FORBIDDEN
	 ngx.header["Content-Type"] =  "text/html"
	 ngx.say('<html><head><title>403 Forbidden</title></head><body><center><h1>403 Forbidden</h1></center><hr><center>nginx'.. error_message .. '</center></body><html>')
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

function lock_cache(auth_md5, username)
    local path = github_auth_cache_dir .. "/" .. auth_md5 .. ".lock"
    local status = os.execute("mkdir " .. path .. " 2> /dev/null")

    if status ~= 0 then
        -- Someone else is already in the process of updating this cache entry.
        -- Wait for the entry to be there.
        ngx.log(ngx.DEBUG, "cache write already locked for " .. username .. " (" .. auth_md5  .. "), waiting")
        while read_cache(auth_md5) == nil do
            ngx.sleep(0.1)
        end
        ngx.log(ngx.DEBUG, "cache for " .. username .. " (" .. auth_md5  .. ") ready for read, wait is over")
    else
        ngx.log(ngx.DEBUG, "cache write locked for " .. username .. " (" .. auth_md5  .. ")")
    end
end

function unlock_cache(auth_md5, username)
    local path = github_auth_cache_dir .. "/" .. auth_md5 .. ".lock"
    os.execute("rmdir " .. path .. " 2> /dev/null")
    ngx.log(ngx.DEBUG, "cache write unlocked for " .. username .. " (" .. auth_md5  .. ")")
end

function check_github(auth_md5, username)
    ngx.log(ngx.STDERR, "checking github for " .. username .. " (" .. auth_md5  .. ")")

    -- authenticate
    --
    local res = ngx.location.capture("/force_github_request/user")
    local username_from_token = nil
    if res.status == 200 then
        username_from_token = string.match(res.body, '"login": "([^"]+)",')
    end
    if res.status ~= 200 or username ~= username_from_token then
        ngx.log(ngx.STDERR, "authentication failed for " .. username .. " (" .. res.status .. ")")
        return "FORBIDDEN"
    end

    -- authorize
    --
    local res = ngx.location.capture("/force_github_request/orgs/" .. github_api_company .. "/members/" .. username)
    if res.status ~= 204 then
        ngx.log(ngx.STDERR, "authorization failed for " .. username .. " (" .. res.status .. ")")
        return "FORBIDDEN"
    end

    return "GRANTED"
end

function authenticate_and_authorize(auth)
    local divider = auth:find(':')
    local username = auth:sub(0, divider-1)
    local token = auth:sub(divider+1)
    local auth_md5 = ngx.md5(auth)

    if local_bot_creds_enabled == true and username == bot_username then
        if token == bot_token then
            return true
        end
        ngx.log(ngx.STDERR, '\nUser ' .. username .. ' not allowed (forbidden by local bot creds)\n')
        return false
    end

    local cache_hit = false
    local cached_status = read_cache(auth_md5)

    if cached_status == nil then
        -- No entry found in cache, do a cache write lock for this entry
	--
        lock_cache(auth_md5, username)

	-- Check if the cache has been populated in the meantime
	--
        cached_status = read_cache(auth_md5)

	if cached_status == nil then
            -- Still no cache entry, make a github request
	    --
	    local status = check_github(auth_md5, username)
	    -- Update cache
	    --
            update_cache(auth_md5, status)
	    cached_status = read_cache(auth_md5)
        else
            cache_hit = true
        end

        -- Unlock the cache entry
	--
        unlock_cache(auth_md5, username)

    else
        cache_hit = true
    end


    if cached_status ~= "GRANTED" then
        if cache_hit == true then
            ngx.log(ngx.STDERR, '\nUser ' .. username .. ' not allowed (github auth cache HIT)\n')
        else
	    ngx.log(ngx.STDERR, '\nUser ' .. username .. ' not allowed (github auth cache MISS)\n')
        end
        return false
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

    local user = authenticate_and_authorize(auth)
    if not user then
        return not_allowed()
    end

    if not restriction_check(auth) then
        return not_allowed()
    end
end
