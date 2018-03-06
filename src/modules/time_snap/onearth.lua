local onearth = {}

local md5 = require "md5"
local date_util = require "date"

local socket = require "socket"

local date_template = "%d%d%d%d%-%d%d?%-%d%d?$"
local datetime_template = "%d%d%d%d%-%d%d?%-%d%d?T%d%d?:%d%d?:%d%d?Z$"
local datetime_filename_format = "%Y%j%H%M%S"
local datetime_format = "%Y-%m-%dT%H:%M:%SZ"


-- Utility functions
local function split (sep, str)
    local results = {}
    for value in string.gmatch(str, "([^" .. sep .. "]+)") do
        results[#results + 1] = value
    end
    return results
end

local function get_query_param (param, query_string)
    local query_parts = split("&", query_string)
    local date_string = nil;
    for _, part in pairs(query_parts) do
        local query_pair = split("=", part)
        if string.lower(query_pair[1]) == param then
            return query_pair[2]
        end
    end
    return date_string
end

local function send_response (code, msg_string)
    return msg_string,
    {
        ["Content-Type"] = "application/json"
    },
    code
end

-- Date utility functions
local function add_interval (date, interval_length, interval_size)
    if interval_size == "Y" then
        return date:addyears(interval_length)
    elseif interval_size == "M" then
        return date:addmonths(interval_length)
    end
end

local function find_snap_date_for_fixed_time_interval (start_date, req_date, end_date, interval_length, interval_size)
    local interval_in_sec = interval_size == "S" and interval_length
        or interval_size == "MM" and interval_length * 60
        or interval_size == "H" and interval_length * 60 * 60
        or interval_size == "D" and interval_length * 60 * 60 * 24
        or nil
    local date_diff = date_util.diff(req_date, start_date)
    local closest_interval_date = start_date:addseconds(math.floor(date_diff:spanseconds() / interval_in_sec) * interval_in_sec)
    if closest_interval_date <= end_date then
        return closest_interval_date
    end
end


local function find_snap_date_for_non_fixed_time_interval (start_date, req_date, end_date, interval_length, interval_size)
    local previous_interval_date = start_date
    while true do
        local check_date = add_interval(previous_interval_date:copy(), interval_length, interval_size)
        if check_date > req_date then -- Found snap date
            return previous_interval_date
        end
        if check_date > end_date then -- Snap date isn't in this period
            break
        end
        previous_interval_date = check_date
    end
end

local function get_snap_date (start_date, req_date, end_date, interval_length, interval_size)
    if interval_size == "H" or interval_size == "MM" or interval_size == "S" or interval_size == "D" then
        return find_snap_date_for_fixed_time_interval(start_date, req_date, end_date, interval_length, interval_size)
    else
        return find_snap_date_for_non_fixed_time_interval(start_date, req_date, end_date, interval_length, interval_size)
    end
end

-- Handlers to get layer period and default date information
local function redis_get_all_layers (client)
    local layers = {}
    local cursor = "0"
    local results
    repeat
        cursor, results = unpack(client:scan(cursor, {match = "layer:*"}))
        for _, value in pairs(results) do
            local layer_name = split(":", value)[2]
            layers[layer_name] = not layers[layer_name] and {} or layers[layer_name]
            layers[layer_name].default = client:get("layer:" .. layer_name .. ":default")
            layers[layer_name].periods = client:smembers("layer:" .. layer_name .. ":periods")
        end
    until cursor == "0"
    return layers
end

local function redis_handler (options)
    local redis = require 'redis'
    local client = redis.connect(options.host, options.port or 6379)
    closeFunc = function()
        client:quit()
    end
    return function (layer_name, uuid)
        local returnValue
        local start_db_request = socket.gettime() * 1000 * 1000
        if layer_name then
            local default = client:get("layer:" .. layer_name .. ":default")
            local periods = client:smembers("layer:" .. layer_name .. ":periods")
            if default and periods then
                returnValue = {[layer_name] = {
                    default = default,
                    periods = periods
                }}
            else
                returnValue = {err_msg = "Layer not found!"}
            end
        else
            -- If no layer name specified, dump all data
            returnValue = redis_get_all_layers(client)
        end
        print(string.format("step=time_database_request duration=%d uuid=%s", socket.gettime() * 1000 * 1000 - start_db_request, uuid))
        return returnValue
    end
end

-- Handlers to format output filenames
local function hash_formatter ()
    return function (layer_name, date)
        local date_string = date:fmt(datetime_filename_format)
        local base_filename_string = layer_name .. "-" .. date_string
        local hash = md5.sumhexa(base_filename_string):sub(0, 4)
        local filename_string = hash .. "-" .. layer_name .. "-" .. date_string
        return filename_string
    end
end


-- Main date snapping handler -- this returns a function that's intended to be called by mod_ahtse_lua
function onearth.date_snapper (layer_handler_options, filename_options)
    local JSON = require("JSON")
    local layer_handler = layer_handler_options.handler_type == "redis" and redis_handler(layer_handler_options) or nil
    local filename_handler = filename_options.filename_format == "hash" and hash_formatter(filename_options)
        or nil
    return function (query_string, headers, _)
        local uuid = headers["UUID"] or "none"
        local start_timestamp = socket.gettime() * 1000 * 1000
        local layer_name = query_string and get_query_param("layer", query_string) or nil

        -- A blank query returns the entire list of layers and periods
        if not query_string or not layer_name then
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(layer_handler(nil, uuid)))
        end

        -- A layer but no date returns the default date and available periods for that layer
        local request_date_string = get_query_param("datetime", query_string)
        local layer_datetime_info = layer_handler(layer_name, uuid)
        if not request_date_string then
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 * 1000- start_timestamp, uuid))
            return send_response(200, JSON:encode(layer_datetime_info))
        end

        -- If it's a default request, return the default date and associated period
        if string.lower(request_date_string) == "default" then
            local default_date = date_util(layer_datetime_info[layer_name].default)
            local out_msg = {
                date = default_date:fmt(datetime_format),
                filename = filename_handler(layer_name, default_date)}
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Send error message if date is in a bad format
        if not string.match(request_date_string, date_template) and not string.match(request_date_string, datetime_template) then
            local out_msg = {
                err_msg = "Invalid Date"
            }
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Send error message if we can't parse the date for any other reason
        local pass, req_date = pcall(date_util, request_date_string)
        if not pass then
            local out_msg = {
                err_msg = "Invalid Date"
            }
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Find snap date if date request is valid
        local snap_date
        for _, period in ipairs(layer_datetime_info[layer_name].periods) do
            local parsed_period = split("/", period)
            local start_date = date_util(parsed_period[1])

            if parsed_period[2] then -- this is a period, so look at both dates
                local end_date = date_util(parsed_period[2])

                -- If period has a single date and it doesn't match, skip it
                if req_date == start_date then
                    snap_date = req_date
                    break
                end
                if req_date > start_date then
                    local interval_length = tonumber(string.match(parsed_period[3], "%d+"))
                    local interval_size = string.match(parsed_period[3], "%a+$")
                    snap_date = get_snap_date(start_date:copy(), req_date, end_date, interval_length, interval_size)
                    break
                end
            else -- this is a single date, so just check if it matches
                if req_date == start_date then
                    snap_date = req_date
                    break
                end
            end
        end

        -- Return snap date and error if none is found
        if snap_date then
            local snap_date_string = snap_date:fmt(datetime_format)
            local out_msg = {
                date = snap_date_string,
                filename = filename_handler(layer_name, snap_date)}
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        else
            local out_msg = {
                err_msg = "Date out of range"
            }
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        end
    end
end
return onearth
