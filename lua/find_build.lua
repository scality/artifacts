-- Init.
--
local expected_status = ngx.var.expected_status
local build_prefix = ngx.var.prefix
local builds = {}

-- Grab builds.
--
local url = "/force_real_request/download/?format=text"
local res = ngx.location.capture(url)
local body = res.body
for build in body:gmatch("([^\r\n]*)[\r\n]*") do
  if build:sub(1, #build_prefix) == build_prefix and build:sub(-1) == "/" then
    table.insert(builds, build)
  end
end

-- Sort builds.
--
table.sort(builds)

-- Find the first build matching expected_status, starting from the latest.
--
for i = #builds, 1, -1 do
  local redirect = true
  if expected_status ~= "" then
    local url = "/force_real_request/download/" .. builds[i] .. ".final_status"
    local res = ngx.location.capture(url)
    local body = res.body
    if body ~= expected_status then
      redirect = false
    end
  end
  if redirect then
    local url = "/download/" .. builds[i]
    if ngx.var.http_script_name ~= nil then
      url = ngx.var.http_script_name:gsub('(.)%/$', '%1') .. url
    end
    return ngx.redirect(url, ngx.HTTP_MOVED_TEMPORARILY);
  end
end

-- If there is no match, send a 404.
--
return ngx.exit(ngx.HTTP_NOT_FOUND);
