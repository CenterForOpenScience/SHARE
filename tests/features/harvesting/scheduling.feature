Feature: Harvester Scheduling

  Scenario Outline: Scheduling harvests
    Given a source config, neat.o, that harvests <INTERVAL>
    And the last harvest of neat.o was <PREVIOUS END DATE>
    When harvests are scheduled on <DATE>
    Then neat.o will have <NUM> harvest logs

    Examples:
      | INTERVAL    | PREVIOUS END DATE | DATE       | NUM |
      | daily       | 2017-01-01        | 2017-01-02 | 2   |
      | daily       | 2017-01-01        | 2017-01-03 | 3   |
      | daily       | 2016-01-01        | 2017-01-01 | 367 |
      | weekly      | 2017-01-01        | 2017-01-03 | 1   |
      | weekly      | 2017-01-01        | 2017-01-08 | 2   |
      | weekly      | 2017-01-01        | 2017-01-09 | 2   |
      | monthly     | 2017-01-01        | 2017-01-09 | 1   |
      | monthly     | 2017-01-01        | 2017-02-09 | 2   |
      | monthly     | 2017-01-01        | 2017-03-02 | 3   |
      | fortnightly | 2017-01-01        | 2017-01-15 | 2   |
      | fortnightly | 2016-12-28        | 2017-01-01 | 1   |
      | fortnightly | 2016-12-28        | 2017-02-01 | 3   |
      | yearly      | 2016-02-01        | 2017-02-01 | 2   |
      | yearly      | 2016-02-01        | 2017-01-29 | 1   |

  # We need a new term for backharvest
  Scenario Outline: Automatically scheduling back harvests
    Given a source config, neat.o, that harvests <INTERVAL>
    And neat.o is allowed to be backharvested
    And neat.o's earliest record is <EARLIEST RECORD>
    When harvests are scheduled on 2017-01-01
    Then neat.o will have <NUM> harvest logs

    Examples:
      | INTERVAL | EARLIEST RECORD | NUM  |
      | daily    | 2000-01-01      | 6210 |
      | weekly   | 1990-01-01      | 1408 |
      | monthly  | 2014-05-07      | 32   |
      | yearly   | 2001-01-01      | 16   |

  Scenario Outline: Scheduling first time harvests
    Given a source config, neat.o, that harvests <INTERVAL>
    When harvests are scheduled on 2017-01-01
    Then neat.o will have 1 harvest logs

    Examples:
      | INTERVAL    |
      | daily       |
      | weekly      |
      | fortnightly |
      | yearly      |

  Scenario Outline: Scheduling idempotency
    Given a source config, neat.o, that harvests <INTERVAL>
    When harvests are scheduled on 2017-01-02
    And harvests are scheduled on 2017-01-02
    And harvests are scheduled on 2017-01-01
    And harvests are scheduled on 2017-01-01
    Then neat.o will have 1 harvest logs

    Examples:
      | INTERVAL    |
      | daily       |
      | weekly      |
      | fortnightly |
      | yearly      |
