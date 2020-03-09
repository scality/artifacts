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

local total_number_of_objects = 0
for object in res.body:gmatch("([^\r\n]+)[\r\n]+") do
  total_number_of_objects = total_number_of_objects + 1
end
local current_object = 0
for object in res.body:gmatch("([^\r\n]+)[\r\n]+") do
  local object_url, object_res

  current_object = current_object + 1
  ngx.say("[" .. current_object .. "/" .. total_number_of_objects .. "] Copying " .. object .. " ... ")
  ngx.flush(true)

  object_url = "/force_real_request/copy/" .. build_src .. "/" .. build_tgt .. "/" .. object
  object_res = ngx.location.capture(object_url, { method = ngx.HTTP_PUT, body = '' })

  if object_res.status == 200 then
    ngx.say('DONE')
    ngx.flush(true)
  else
    ngx.say('FAILED')
    ngx.flush(true)
    return
  end
end

ngx.say("BUILD COPIED")
