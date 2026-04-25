# Ownership Map

Ownership mapping routes technical findings to the right accountable group.

## Standard Module Mapping

| Table or Area | Business Owner | Technical Owner |
| --- | --- | --- |
| `InventTrans`, `InventSum`, `InventDim` | Supply Chain / Inventory | AX Operations |
| `CustTrans`, `VendTrans` | Finance / AR / AP | AX Operations |
| `GeneralJournalAccountEntry`, `LedgerJournalTrans` | Finance / General Ledger | AX Operations |
| `SalesTable`, `SalesLine` | Sales Operations | AX Operations |
| `PurchTable`, `PurchLine` | Procurement | AX Operations |
| `Batch`, `BatchJob`, `BatchHistory` | IT Operations | AX Operations |
| Retail transaction and statement tables | Retail Operations | AX/Retail Operations |
| AIF, EDI, staging, and service tables | Integration Owner | Integration Team |
| Workflow history and tracking | Process Owner | AX Operations |
| Custom tables/classes/reports | Owning Business Process | AX Development / Vendor |

## Routing Rules

- If a finding involves a custom object, route to the customization owner first.
- If ownership is unknown, mark the finding as `owner-required` and include the object names.
- If the finding affects multiple modules, assign a primary owner by business impact and list secondary stakeholders.
- If the finding requires database change approval, include DBA ownership in the change path.
- If the finding affects validated business processes, include QA or validation ownership in the approval path.
