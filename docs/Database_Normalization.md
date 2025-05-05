# Database Normalization: Schema Types and Examples

> Database normalization is a process of organizing data to reduce redundancy and improve data integrity. Here are the main normal forms with examples:

## 1NF (First Normal Form)

> Rule: Each table cell should contain a single value and each record needs to be unique.

### Before 1NF:

Customer_Orders
CustomerID | CustomerName | Orders
---------------------------------
1          | John Smith   | Book, Pen
2          | Jane Doe     | Laptop, Mouse, Keyboard

### After 1NF:

Customer_Orders
CustomerID | CustomerName | Order
--------------------------------
1          | John Smith   | Book
1          | John Smith   | Pen
2          | Jane Doe     | Laptop
2          | Jane Doe     | Mouse
2          | Jane Doe     | Keyboard

## 2NF (Second Normal Form)

Rule: Must be in 1NF and all non-key attributes must depend on the entire primary key.

### Before 2NF:

Order_Details
OrderID | ProductID | ProductName | CustomerID | CustomerAddress
----------------------------------------------------------
1       | P1        | Laptop      | C1         | 123 Main St
1       | P2        | Mouse       | C1         | 123 Main St

### After 2NF:

Orders
OrderID | CustomerID
--------------------
1       | C1

Customers
CustomerID | CustomerAddress
--------------------------
C1         | 123 Main St

Products
ProductID | ProductName
----------------------
P1        | Laptop
P2        | Mouse

Order_Details
OrderID | ProductID
-------------------
1       | P1
1       | P2

## 3NF (Third Normal Form)

Rule: Must be in 2NF and no transitive dependencies (non-key attributes depending on other non-key attributes).

### Before 3NF:

Employee
EmpID | EmpName | DeptID | DeptName | DeptLocation
------------------------------------------------
1     | John    | D1     | Sales    | New York
2     | Jane    | D1     | Sales    | New York

### After 3NF:

Employee
EmpID | EmpName | DeptID
------------------------
1     | John    | D1
2     | Jane    | D1

Department
DeptID | DeptName | DeptLocation
--------------------------------
D1     | Sales    | New York
BCNF (Boyce-Codd Normal Form)

Rule: Must be in 3NF and every determinant must be a candidate key.

### Before BCNF:

Student_Course
StudentID | Course | Professor
------------------------------
S1        | Math   | Prof Smith
S2        | Math   | Prof Smith
S3        | CS     | Prof Jones

### After BCNF:

Course_Professor
Course | Professor
------------------
Math   | Prof Smith
CS     | Prof Jones

Student_Course
StudentID | Course
------------------
S1        | Math
S2        | Math
S3        | CS

## 4NF (Fourth Normal Form)

Rule: Must be in BCNF and have no multi-valued dependencies.

### Before 4NF:

Student_Skills_Languages
StudentID | Skill        | Language
----------------------------------
S1        | Programming  | English
S1        | Programming  | Spanish
S1        | Design      | English
S1        | Design      | Spanish

### After 4NF:

Student_Skills
StudentID | Skill
-------------------
S1        | Programming
S1        | Design

Student_Languages
StudentID | Language
--------------------
S1        | English
S1        | Spanish

## 5NF (Fifth Normal Form)

Rule: Must be in 4NF and have no join dependencies that are not implied by candidate keys.

### Before 5NF:

Sales_Agent_Product_Region
AgentID | ProductID | RegionID
--------------------------------
A1      | P1        | R1
A1      | P2        | R2
A2      | P1        | R1

### After 5NF:

Agent_Product
AgentID | ProductID
-------------------
A1      | P1
A1      | P2
A2      | P1

Agent_Region
AgentID | RegionID
------------------
A1      | R1
A1      | R2
A2      | R1

Product_Region
ProductID | RegionID
-------------------
P1        | R1
P2        | R2

## Key Benefits of Normalization

+ Eliminates data redundancy
+ Ensures data consistency
+ Ensures data consistency
+ Reduces storage space
+ Simplifies data maintenance
+ Improves data integrity

## Trade-offs

+ Higher normalization can lead to more complex queries
+ May impact query performance due to increased table joins
+ Should balance normalization with practical requirements