# Import a circuit screenshot

Open **Import a circuit screenshot**. Upload a PNG, JPEG or WEBP image, enter an OpenAI API key and press **Analyze image with OpenAI**. API usage is billed separately by OpenAI. An administrator can instead configure OPENAI_API_KEY on the server. Do not send anyone your key or include it in a saved drawing.

The app sends the image to OpenAI only when you press Analyze. It requests a structured netlist, then builds a proposed schematic locally. Compare the original image and preview. Edit the component table to correct values, source polarity/current direction, node names, amplifier settings or connections. Fill unreadable values; use node 0 as ground. Confirm the review checkbox and click **Load reviewed circuit**. Changing the table changes the approval checkbox, so edits must be reviewed again. Loading replaces the active drawing; save your old circuit first.

The result is an editable schematic with explicit terminal connections. It preserves the reviewed electrical netlist rather than the screenshot's exact page layout. You can move parts and reroute wires afterward. The app does not solve the imported drawing until you request a solve, and the ordinary floating-node, source-conflict, feedback and rail checks still apply.

## Supported input and limits

- Resistors, independent DC voltage/current sources, ideal op amps and output probes.
- At most 24 components, 40 nodes and 8 MB per image; images must be at most 16 megapixels.
- Uploaded images are converted to a JPEG no larger than 2048 × 2048 before analysis. Crop tightly enough to keep small values readable.
- Source values use SI units: Ω, volts and amperes. Voltage source node1 is positive; current source direction is node1 → node2. Op amp node1 = +, node2 = −, node3 = OUT.
- Unknown numeric values, op-amp mode and output limits require explicit review; the app does not silently fill them.
- Reported unsupported symbols block loading instead of being silently omitted. Capacitors, inductors, AC/controlled sources and semiconductor models are outside this importer.

Recognition can confuse wire crossings, junction dots, handwritten symbols, values and source polarity. The review step is required even if there are no reported ambiguities. A successful transcription is not proof the original diagram was read correctly.

## Model and privacy

The configurable default is **gpt-5.6-terra**, using OpenAI's Responses API with image input and a strict JSON schema. Choose a model available to your API account that supports both image input and structured outputs. Errors report billing, access or connection problems without echoing the key or raw provider response. Requests set `store=false`; consult OpenAI's data policies for provider-side handling. Keys remain in local configuration or the live app session and are not included in drawing JSON or exports.

## What was tested

Unit tests cover image preparation, the HTTP request/response contract using a fake transport, invalid input, refusals, incomplete output, explicit settings, key/error handling and reconstruction of actual editable wiring. Streamlit and real-browser checks cover review approval and loading. The browser also uploads a valid test PNG without making an API call.

**Live screenshot recognition was not run in this release because no API key was supplied.** The offline **Try import review demo (no API)** button uses a predefined divider netlist to demonstrate the review screen; it does not claim to recognize an image. On your machine, verify the first real transcription against a known simple circuit before using it for homework.

Official API references:
https://developers.openai.com/api/docs/guides/images-vision
https://developers.openai.com/api/docs/guides/structured-outputs
https://developers.openai.com/api/docs/models/gpt-5.6-terra
