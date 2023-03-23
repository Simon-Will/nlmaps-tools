# nlmaps-tools

Tools for working with [NLMaps](https://nlmaps.org/) data structures.

## Processing Tool

To transform some form of a query into another, you can use the `ProcessingTool`, also via the command line by
executing `python3 -m nlmaps_tools.process`.

### Example: Turn MRL into Overpass queries and results

```
python3 -m nlmaps_tools.process \
    --wanted MultiAnswer --wanted Will2021Features \
    --given "Will2021Lin=query(area(keyval('name','Paris')),nwr(keyval('amenity','bar')),qtype(latlong))"
```