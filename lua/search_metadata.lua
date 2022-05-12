-- Metadata objects format in staging bucket:
--
-- /.md_staging/$(repo)/LIST/$(timestamp)/$(artifacts_name)
-- /.md_staging/$(repo)/MD/$(key)/__$(value)__/WF/$(workflow_name)/LIST/$(timestamp)/$(artifacts_name)

-- Input checks
--
local search_mode, key, repo, workflow, value = string.match(ngx.var.canonical_path, "^([^/]+)/([^/]+)/([^/]+/[^/]+/[^/]+)/([^/]+)/(.+)$")
if search_mode ~= "list" and search_mode ~= "latest" and search_mode ~= "last_success" then
  ngx.exit(ngx.HTTP_BAD_REQUEST)
end

local function check_build_status(artifacts_name)
  url = "/force_real_request/download/" .. artifacts_name .. "/.final_status"
  res = ngx.location.capture(url)
  if res.status == 200 then
    return res.body
  elseif res.status == 404 then
    return "INCOMPLETE"
  else
    return nil
  end
end

-- Get builds list
--
local url, res, body
url = "/force_real_request/download/.md_staging/" .. repo .. "/MD/" .. key .. "/__" .. value .. "__/WF/" .. workflow .. "/LIST/?format=txt"
res = ngx.location.capture(url)
if res.status ~= 200 then
  ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end
local body = res.body
local builds = {}
for build in body:gmatch("([^\r\n]+)[\r\n]+") do
  table.insert(builds, build)
end
table.sort(builds)

-- Process results
--
local uniq_list = {}
for i = #builds, 1, -1 do
  local artifacts_name = string.match(builds[i], "^[^/]+/([^/]+)$")
  if artifacts_name ~= nil then
    if search_mode ~= "list" then
      local res = check_build_status(artifacts_name)
      if res ~= nil then
        if (search_mode == "last_success" and res == "SUCCESSFUL") or (search_mode == "latest" and res ~= "INCOMPLETE") then
          ngx.say(artifacts_name)
          ngx.flush(true)
	  break
        end
      end
    else
      -- Remove duplicates
      --
      if uniq_list[artifacts_name] == nil then
        ngx.say(artifacts_name)
        ngx.flush(true)
        uniq_list[artifacts_name] = true
      else
        ngx.log(ngx.STDERR, "found multiple timestamps for " .. artifacts_name .. " metadata")
      end
    end
  end
end
