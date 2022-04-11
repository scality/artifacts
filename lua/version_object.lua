-- Grab version and object.
--

local version, build, object = string.match(ngx.var.canonical_path, "^([^/]+)/([^/]+)/(.*)")

local url, res

-- Check if the object is already present.
--
ngx.say('CHECK IF THE OBJECT IS ALREADY UPLOADED...')
ngx.flush(true)
url = "/force_real_request/download/" .. build .. "/" .. object
res = ngx.location.capture(url)
if res.status == 404 then
  ngx.say('OBJECT NOT FOUND')
  ngx.say('PASSED')
  ngx.flush(true)
  return
elseif res.status == 200 then
  ngx.say('OBJECT FOUND')
  ngx.flush(true)
else
  ngx.say('INTERNAL ERROR')
  ngx.say('FAILED')
  ngx.flush(true)
  return
end

-- Check if the versioned object is already present.
--
ngx.say('CHECK IF THE OBJECT IS ALREADY VERSIONED...')
ngx.flush(true)
url = "/force_real_request/download/" .. build .. "/.ARTIFACTS_BEFORE/" .. version .. "/" .. object
res = ngx.location.capture(url)
if res.status == 404 then
  ngx.say('VERSIONED OBJECT NOT FOUND')
  ngx.flush(true)
elseif res.status == 200 then
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
else
  ngx.say('INTERNAL ERROR')
  ngx.say('FAILED')
  ngx.flush(true)
end
