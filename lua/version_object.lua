-- Grab version and object.
--

local version, build, object = string.match(ngx.var.canonical_path, "^([^/]+)/([^/]+)/(.*)?")

local url, res

-- Check if the versioned object is already present.
--
url = "/force_real_request/download/" .. build .. "/.ARTIFACTS_BEFORE/" .. version .. "/" .. object
res = ngx.location.capture(url)
if res.status == 200 then
  ngx.say('OBJECT ALREADY VERSIONED, SKIPPING')
  ngx.flush(true)
  return
else
  ngx.say('OBJECT CAN BE VERSIONED')
  ngx.flush(true)
end

-- Copy the object to the versioned object location.
--
ngx.say('VERSIONING THE OBJECT')
ngx.flush(true)
object_url = "/force_real_request/copy/" .. build .. "/" .. build .. "/.ARTIFACTS_BEFORE/" .. version .. "/" .. object
object_res = ngx.location.capture(object_url, { method = ngx.HTTP_PUT, body = '' })
if object_res.status == 200 then
  ngx.say('DONE')
  ngx.flush(true)
else
  ngx.say('FAILED')
  ngx.flush(true)
  return
end

ngx.say('OBJECT VERSIONED')
