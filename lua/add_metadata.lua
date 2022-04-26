-- Metadata objects format in staging bucket:
--
-- /.METADATA/$(repo)/LIST/$(timestamp)/$(artifacts_name)
-- /.METADATA/$(repo)/METADATA/$(key)/__$(value)__/STAGE/$(stage)/LIST/$(timestamp)/$(artifacts_name)

-- Input checks
--
local repo, stage, timestamp, artifacts_name = string.match(ngx.var.canonical_path, "^([^/]+/[^/]+/[^/]+)/([^/]+)/([^/]+)/([^/]+)$")
if repo == nil or stage == nil or timestamp == nil or artifacts_name == nil then
  ngx.exit(ngx.HTTP_BAD_REQUEST)
end

local function generate_object_path (repo, stage, timestamp, artifacts_name, key, value)
  local object_path = ".METADATA/"
  if key == nil then
    object_path = object_path .. repo .. "/LIST/" .. timestamp .. "/" .. artifacts_name
  else
    object_path = object_path .. repo .. "/METADATA/" .. key .. "/__" .. value .. "__/STAGE/" .. stage .. "/LIST/" .. timestamp .. "/" .. artifacts_name
  end
  return object_path
end

local function add_metadata (repo, stage, timestamp, artifacts_name, key, value)
  if key == nil then
    ngx.say('adding ' .. artifacts_name .. ' to time sorted listing')
  else
    ngx.say('adding metadata ' .. key .. '=' .. value .. ' for ' .. artifacts_name)
  end
  ngx.flush(true)
  local object_path = generate_object_path(repo, stage, timestamp, artifacts_name, key, value)
  url = "/force_real_request/upload/" .. object_path
  res = ngx.location.capture(url,  { method = ngx.HTTP_PUT, body = '' })
  if res.status == 200 then
    ngx.say('DONE')
    ngx.flush(true)
    return true
  else
    ngx.say('FAILED')
    ngx.flush(true)
    return false
  end
end

local function get_metadata_list ()
  local query_string = ngx.var.query_string
  local metadata = {}
  if query_string ~= nil then
    for key, value in query_string:gmatch('([^&=]+)=([^&=]+)')  do
      if key:match("/") then
        ngx.log(ngx.ERR, "invalid key ('/' character found): '" .. key .. "'")
        ngx.exit(ngx.HTTP_BAD_REQUEST)
      end
      if value:match("//") then
        ngx.log(ngx.ERR, "invalid value ('//' sequence found): '" .. value .. "'")
        ngx.exit(ngx.HTTP_BAD_REQUEST)
      end
      table.insert(metadata, { key, value })
    end
  end
  return metadata
end

-- Loop
--
local metadata = get_metadata_list()
if add_metadata(repo, stage, timestamp, artifacts_name, nil, nil) == false then
  return
end
for i = 1, #metadata do
    if add_metadata(repo, stage, timestamp, artifacts_name, metadata[i][1], metadata[i][2]) == false then
      return
    end
end
ngx.say('PASSED')
ngx.flush(true)
