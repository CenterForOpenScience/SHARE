Feature: Custom Subject Taxonomy

    Background:
        Given a user with a source
        And a central taxonomy
            | NAME | PARENT |
            | A    |        |
            | A1   | A      |
            | A2   | A      |
            | A2a  | A2     |
            | A2b  | A2     |
            | A3   | A      |
            | B    |        |
            | B1   | B      |
            | B2   | B      |
        And a custom taxonomy
            | NAME | PARENT | SYNONYM |
            | cA   |        | A       |
            | cA1  | cA     | A1      |
            | cA2  | cA     | A2      |
            | cAB  | cA     | B       |

    Scenario:
        Verify background worked.

        Then central taxonomy exists
        And custom taxonomy exists
        And 13 subjects exist
        And 9 subjects exist in central taxonomy
        And 4 subjects exist in custom taxonomy
        And 3 root subjects exist
        And 2 root subjects exist in central taxonomy
        And 1 root subjects exist in custom taxonomy
        And A is a root
        And A1 is a child of A
        And cA is a root
        And cA1 is a child of cA
        And cA1 is a synonym of A1
        And A has depth 1
        And A1 has depth 2
        And A2a has depth 3
        And cA has depth 1
        And cA1 has depth 2
        And cA2 has depth 2

    Scenario:
        Add work with no subject changes.

        When a work is added with subjects
            | NAME | PARENT | SYNONYM |
            | B1   |        |         |
            | cA   |        | A       |
            | cA1  | cA     | A1      |
            | cA2  | cA     | A2      |
        Then 13 subjects exist
        And 4 subjects exist in custom taxonomy
        And 1 root subjects exist in custom taxonomy

    Scenario:
        Changing a subject's parent.

        When a work is added with subjects
            | NAME | PARENT | SYNONYM |
            | cA   |        | A       |
            | cA1  | cA     | A1      |
            | cA2  | cA1    | A2      |
        Then cA2 is a child of cA1
        And cA1 is a child of cA
        And cA has depth 1
        And cA1 has depth 2
        And cA2 has depth 3

    Scenario:
        Changing a custom subject's synonym.

        When a work is added with subjects
            | NAME | PARENT | SYNONYM |
            | cA   |        | A       |
            | cA1  | cA     | B1      |
            | cA2  | cA     | B2      |
        Then cA1 is a synonym of B1
        And cA2 is a synonym of B2
        And cA is a synonym of A

    Scenario:
        Add a custom subject.

        When a work is added with subjects
            | NAME | PARENT | SYNONYM |
            | cA   |        | A       |
            | cA1  | cA     | A1      |
            | cA3  | cA1    | A3      |
        Then 14 subjects exist
        And 5 subjects exist in custom taxonomy
        And cA3 is a child of cA1
        And cA1 is a child of cA
        And cA has depth 1
        And cA1 has depth 2
        And cA3 has depth 3
        And cA3 is a synonym of A3
