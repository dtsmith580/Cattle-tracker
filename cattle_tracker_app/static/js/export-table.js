function exportTable(type) {
  const table = document.querySelector('.table-container table');
  const rows = [...table.rows].map(row => [...row.cells].map(cell => cell.innerText));

  if (type === 'csv' || type === 'excel') {
    const content = rows.map(e => e.join(",")).join("\n");

    const mime = type === 'excel' ? 'application/vnd.ms-excel' : 'text/csv';
    const fileContent = `data:${mime};charset=utf-8,` + content;
    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(fileContent));
    link.setAttribute("download", `table_export.${type === 'excel' ? 'xls' : 'csv'}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } else if (type === 'pdf') {
    const printWindow = window.open('', '', 'width=800,height=600');
    printWindow.document.write('<html><head><title>Export PDF</title>');
    printWindow.document.write('<style>table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #000; padding: 4px; }</style>');
    printWindow.document.write('</head><body >');
    printWindow.document.write(table.outerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
  } else if (type === 'print') {
    const printWindow = window.open('', '', 'width=800,height=600');
    printWindow.document.write('<html><head><title>Print Table</title>');
    printWindow.document.write('<style>table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #000; padding: 4px; }</style>');
    printWindow.document.write('</head><body >');
    printWindow.document.write(table.outerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
  }
}
