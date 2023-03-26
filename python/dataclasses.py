# General hacks for dataclasses

# Only populate known fields but using a generic dict that can contain all sorts of things
import dataclasses
return SomeDataClass({field.name: some_dict.get(field.name) for field in dataclasses.fields(SomeDataClass)})
