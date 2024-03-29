-- Grab version and object.
--

local version, build, object = string.match(ngx.var.canonical_path, "^([^/]+)/([^/]+)/(.*)")

local url, res

-- Check if the versioned object is already present (see nginx conf to see how /check/ behaves, as it is a bit hackish).
--
ngx.say('CHECK IF THE OBJECT IS ALREADY VERSIONED...')
ngx.flush(true)
url = "/force_real_request/check_raw/" .. build .. "/.ARTIFACTS_BEFORE/" .. version .. "/" .. object
res = ngx.location.capture(url)
if res.status == 404 then
  ngx.say('VERSIONED OBJECT NOT FOUND')
  ngx.flush(true)
elseif res.status == 416 then
  ngx.say('VERSIONED OBJECT FOUND')
  ngx.say('PASSED')
  ngx.flush(true)
  return
else
  ngx.say('INTERNAL ERROR')
  ngx.say('FAILED')
  ngx.flush(true)
  return
end

-- Copy the object to the versioned object location.
--
ngx.say('VERSIONING THE OBJECT...')
ngx.flush(true)
object_url = "/force_real_request/copy/" .. build .. "/" .. build .. "/.ARTIFACTS_BEFORE/" .. version .. "/" .. object
object_res = ngx.location.capture(object_url, { method = ngx.HTTP_PUT, body = '' })
if object_res.status == 200 then
  ngx.say('DONE')
  ngx.say('PASSED')
  ngx.flush(true)
elseif object_res.status == 404 then
  ngx.say('SOURCE OBJECT NOT FOUND')
  ngx.say('PASSED')
  ngx.flush(true)
else
  ngx.say('INTERNAL ERROR')
  ngx.say('FAILED')
  ngx.flush(true)
end
