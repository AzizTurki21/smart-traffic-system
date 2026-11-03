# Message formats

The report names the MQTT topics but does not define the original payload schema. These JSON payloads are a new, explicit contract for this reconstruction.

## `SMdetection`

One detection event per cooldown window:

```json
{"lane":"lane2","class":"ambulance","confidence":0.91,"camera":1,"timestamp":1730000000.0}
```

The controller accepts only configured priority classes and lane names. A malformed event is ignored and logged.

## `SMTraffic`

Published approximately once per second:

```json
{"mode":"normal","active_lane":"lane2","remaining_s":4,"lanes":{"lane1":"red","lane2":"green","lane3":"red"},"timestamp":1730000000.0}
```

During an emergency hold, `mode` is `priority` and `active_lane` is the detected approach. The LoRa transmitter forwards the JSON text unchanged. Keep the payload compact enough for the selected LoRa data rate.

## RFID tags

RFID UIDs are not present in the report. The receiver sketch prints unknown tag UIDs to Serial. Add the observed UIDs to its `LANE_TAGS` and `INTERSECTION_TAG` definitions after scanning your own tags.
