-- https://artifacts.scality.net/search/branch/github/scality/ring/workflow-name/development/7.4/latest_success will return the content of the latest successful artifacts for the given branch
-- https://artifacts.scality.net/search/commit/github/scality/ring/workflow-name/40ba53f2c6065277e2a89e77fdc6d9343159fc6e will return a list of artifacts that correspond to the given shasum
-- https://artifacts.scality.net/search/commit/github/scality/ring/workflow-name/40ba53f2c6 will return a list of artifacts that correspond to the given shasum
-- https://artifacts.scality.net/search/commit/github/scality/ring/workflow-name/40ba53f2c6065277e2a89e77fdc6d9343159fc6e/latest will return the content of the latest artifacts failed or not for the given shasum
-- https://artifacts.scality.net/search/commit/github/scality/ring/workflow-name/40ba53f2c6/latest will return the content of the latest artifacts failed or not for the given shasum
-- https://artifacts.scality.net/search/commit/github/scality/ring/workflow-name/40ba53f2c6065277e2a89e77fdc6d9343159fc6e/latest_success  will return the content of the latest successful artifacts for the given shasum
-- https://artifacts.scality.net/search/commit/github/scality/ring/workflow-name/40ba53f2c6/latest_success will return the content of the latest successful artifacts for the given shasum


--
-- /search/(list|latest|last_success)/(branch|commit|version)/github/scality/(repo)/(workflow_name)/(.*)$
--
--

-- Metadata objects format in staging bucket:
--
-- /.METADATA/$(repo)/LIST/$(timestamp)/$(artifacts_name)
-- /.METADATA/$(repo)/METADATA/$(key)/__$(value)__/STAGE/$(stage)/LIST/$(timestamp)/$(artifacts_name)

-- Input checks
--
local search_mode, key, repo, workflow, value = string.match(ngx.var.canonical_path, "^([^/]+)/([^/]+)/([^/]+/[^/]+/[^/]+)/([^/]+)/(.+)$")
if search_mode ~= "list" and search_mode ~= "latest" and search_mode ~= "last_success" then
  ngx.exit(ngx.HTTP_BAD_REQUEST)
end


-- Get builds list
--
local url, res, body
url = "/force_real_request/download/.METADATA/" .. repo .. "/METADATA/" .. key .. "/__" .. value .. "__/STAGE/" .. workflow .. "/LIST/?format=txt"
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
for i = #builds, 1, -1 do
  ngx.log(ngx.ERR, "index: " .. i)
  ngx.say(builds[i])
  ngx.flush(true)
end
