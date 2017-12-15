Feature: Harvester Laziness
  Harvesting will be as lazy as possible.
  If it can be determined that the system already has
  all the data, the task will be marked as "skipped"

  Background:
    Given the source Neat.io
      And Neat.io has a source config, io.neat
      And a succeeded harvest of io.neat for 2012-11-10 to 2012-11-11
      And a succeeded harvest of io.neat for 2012-11-12 to 2012-11-15

  Scenario Outline: Skippable harvest tasks
    When io.neat is harvested for <START_DATE> to <END_DATE>
    Then io.neat's latest harvest job's status will be skipped
    And it will be completed 2 times
    And it's context will be <REASON>

    Examples:
      | START_DATE | END_DATE   | REASON                       |
      | 2012-11-10 | 2012-11-11 | Previously Succeeded         |
      # Future improvements
      # | 2012-11-13 | 2012-11-14 | Encompassing task succeeded  |
      # | 2012-11-13 | 2012-11-15 | Encompassing task succeeded  |
      # | 2012-11-12 | 2012-11-14 | Encompassing task succeeded  |
      # | 2012-11-10 | 2012-11-15 | Comprised of succeeded tasks |

  Scenario: Version's must match
    Given io.neat is updated to version 2
    When io.neat is harvested for 2012-11-10 to 2012-11-11
    Then io.neat will have 2 harvest jobs for 2012-11-10 to 2012-11-11
    And io.neat's latest harvest job's status will be succeeded

  Scenario Outline: Past harvests must have been successful
    Given a <STATUS> harvest of io.neat for 2012-11-01 to 2012-11-02
    When io.neat is harvested for 2012-11-01 to 2012-11-02
    Then io.neat will have 1 harvest job for 2012-11-01 to 2012-11-02
    And io.neat's latest harvest job's status will be succeeded

    Examples:
      | STATUS  |
      | failed  |
      | skipped |
      | forced  |
