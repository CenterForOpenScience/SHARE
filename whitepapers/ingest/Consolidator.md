# Consolidator (NOT IMPLEMENTED)

TODO: flesh this out more

## Responsibilities
* Update the states of a SUID to match a MutableGraph

## Parameters
* [MutableGraph](./Graph.md) object, successful output from the [Regulator](./Regulator.md)
* SUID

## Steps
* Diff the states
  * A more presumptuous form of disambiguation should be used here to match as many nodes as possible
  * Double check that dates are not going back in time (May be indicitive of a race)
* Create/update the states as necessary
  * Any existing nodes that have had nothing disambiguated to them may be considered removed/deleted
  * Ensure that internal modification dates are not bumped if no changes have been made
