-- Grab src and tgt builds.
--

local build_src, build_tgt = string.match(ngx.var.canonical_path, "([^/]+)/([^/]+)/")

local url, res

-- Check if .final_status is present on build_src.
--
url = "/force_real_request/download/" .. build_src .. "/.final_status"
res = ngx.location.capture(url)
if res.status ~= 200 then
  ngx.say('SOURCE BUILD NOT FINISHED (NO ".final_status" FOUND), ABORTING')
  return
end

-- Check that build_tgt is empty
--
ngx.say("Checking if the target reference '" .. build_tgt .. "' is empty")
ngx.flush(true)
url = "/force_real_request/download/" .. build_tgt .. "/?format=txt"
res = ngx.location.capture(url)
if res.body == "" and res.truncated == false then
  ngx.say('DONE')
  ngx.flush(true)
else
  ngx.say('FAILED')
  ngx.flush(true)
  return
end

-- Add a reference to the original build, if needed.
--
ngx.say("Adding the source reference '" .. build_src .. "' if needed")
ngx.flush(true)
url = "/force_real_request/download/" .. build_src .. "/.original_build"
res = ngx.location.capture(url)
if res.status == 200 then
  ngx.say('DONE')
  ngx.flush(true)
else
  url = "/force_real_request/upload/" .. build_src .. "/.original_build"
  res = ngx.location.capture(url, { method = ngx.HTTP_PUT, body = build_src })
  if res.status == 200 then
    ngx.say('DONE')
    ngx.flush(true)
  else
    ngx.say('FAILED')
    ngx.flush(true)
    return
  end
end

-- Process each object listed in build_src.
--
ngx.say("Listing objects from the source reference '" .. build_src .. "'")
url = "/force_real_request/download/" .. build_src .. "/?format=txt"
res = ngx.location.capture(url)
if res.status == 200 and res.truncated == false then
  ngx.say('DONE')
  ngx.flush(true)
else
  ngx.say('FAILED')
  ngx.flush(true)
  return
end

local objects = {}
for object in res.body:gmatch("([^\r\n]+)[\r\n]+") do
  table.insert(objects, object)
end

local total_number_of_objects = #objects
local batch_size = 16
local current_object = 0

for batch_start = 1, total_number_of_objects, batch_size do
  local batch_end = math.min(batch_start + batch_size - 1, total_number_of_objects)
  local urls = {}
  for i = batch_start, batch_end do
    table.insert(urls, {
      "/force_real_request/copy/" .. build_src .. "/" .. build_tgt .. "/" .. objects[i],
      { method = ngx.HTTP_PUT, body = '' }
    })
  end

  local results = { ngx.location.capture_multi(urls) }

  for i, object_res in ipairs(results) do
    current_object = current_object + 1
    local object = objects[batch_start + i - 1]
    ngx.say("[" .. current_object .. "/" .. total_number_of_objects .. "] " .. object .. " ... ")
    if object_res.status == 200 then
      ngx.say('DONE')
    else
      ngx.say('FAILED')
      ngx.flush(true)
      return
    end
  end
  ngx.flush(true)
end

ngx.say("BUILD COPIED")
