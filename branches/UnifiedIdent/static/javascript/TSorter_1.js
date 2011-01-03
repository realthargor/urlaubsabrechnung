/*--------------------------------------------------------------*/
// HTML TABLE SORTER
// OBJECT ORIENTED JAVASCRIPT IMPLEMENTATION OF QUICKSORT
// @author	Terrill Dent 
// @source	http://www.terrill.ca
// @date	August 28th, 2006
/*--------------------------------------------------------------*/
function TSorter() {
	var table = Object;
	var trs = Array;
	var ths = Array;
	var curSortCol = Object;
	var prevSortCol = -1;

	function get() {
	}

	function getCell(index) {
		return trs[index].cells[curSortCol]
	}

	/*----------------------INIT------------------------------------*/
	// Initialize the variable
	// @param tableName - the name of the table to be sorted
	/*--------------------------------------------------------------*/
	this.init = function(tableName) {
		table = document.getElementById(tableName);
		ths = $$('table#' + tableName + '.sortable th.sortable');
		ths.each(function(header) {
			header.onclick = function() {
				sort(this);
			};
		});
		return true;
	};

	/*----------------------SORT------------------------------------*/
	// Sorts a particular column. If it has been sorted then call reverse
	// if not, then use quicksort to get it sorted.
	// Sets the arrow direction in the headers.
	// @param oTH - the table header cell (<th>) object that is clicked
	/*--------------------------------------------------------------*/
	function sort(oTH) {
		curSortCol = oTH.cellIndex;
		Element.extend(oTH);
		trs = table.tBodies[0].getElementsByTagName("tr");

		// update the get function
		setGet(oTH.abbr)

		// it would be nice to remove this to save time,
		// but we need to close any rows that have been expanded
		for ( var j = 0; j < trs.length; j++) {
			if (trs[j].hasClassName('detail_row')) {
				closeDetails(j + 2);
			}
		}

		// if already sorted just reverse
		if (prevSortCol == curSortCol) {
			if (oTH.hasClassName('ascend')) {
				oTH.removeClassName('ascend');
				oTH.addClassName('descend');
				reverseTable();
			} else if (oTH.hasClassName('descend')) {
				oTH.removeClassName('descend');
				oTH.addClassName('ascend');
				reverseTable();
			}
		} else {
			// not sorted - call quicksort
			oTH.addClassName('ascend');
			quicksort(0, trs.length);
			// remove sort class from previous header
			if (prevSortCol >= 0) {
				prev = ths[prevSortCol];
				Element.extend(prev);
				prev.removeClassName('ascend');
				prev.removeClassName('descend');
			}
		}
		prevSortCol = curSortCol;
	}

	/*--------------------------------------------------------------*/
	// Sets the GET function so that it doesnt need to be
	// decided on each call to get() a value.
	// @param: sortType - the column number to be sorted
	/*--------------------------------------------------------------*/
	function setGet(sortType) {
		switch (sortType) {
		case "link":
			get = function(index) {
				return getCell(index).firstChild.firstChild.nodeValue;
			};
			break;
		case "currency":
			get = function(index) {
				cell = getCell(index);
				if (cell==null) return -3e30;
				child = cell.firstChild;
				if (child==null || child.nodeValue==null) return -3e30;
				s = child.nodeValue.replace(',', '.');
				f = parseFloat(s.replace(/[^0-9.-]/g, ''));				
				if (isNaN(f) || f==0) return -3e30;
				return f;
			};
			break;
		default:
			get = function(index) {
				return getCell(index).firstChild.nodeValue;
			};
			break;
		}
		a = 5;
	}

	/*-----------------------EXCHANGE-------------------------------*/
	// A complicated way of exchanging two rows in a table.
	// Exchanges rows at index i and j
	/*--------------------------------------------------------------*/
	function exchange(i, j) {
		if (i == j + 1) {
			table.tBodies[0].insertBefore(trs[i], trs[j]);
		} else if (j == i + 1) {
			table.tBodies[0].insertBefore(trs[j], trs[i]);
		} else {
			var tmpNode = table.tBodies[0].replaceChild(trs[i], trs[j]);
			if (typeof (trs[i]) == "undefined") {
				table.appendChild(tmpNode);
			} else {
				table.tBodies[0].insertBefore(tmpNode, trs[i]);
			}
		}
	}

	/*----------------------REVERSE TABLE----------------------------*/
	// Reverses a table ordering
	/*--------------------------------------------------------------*/
	function reverseTable() {
		for ( var i = 1; i < trs.length; i++) {
			table.tBodies[0].insertBefore(trs[i], trs[0]);
		}
	}

	/*----------------------QUICKSORT-------------------------------*/
	// This quicksort implementation is a modified version of this tutorial:
	// http://www.the-art-of-web.com/javascript/quicksort/
	// @param: lo - the low index of the array to sort
	// @param: hi - the high index of the array to sort
	/*--------------------------------------------------------------*/
	function quicksort(lo, hi) {
		if (hi <= lo + 1)
			return;

		if ((hi - lo) == 2) {
			if (get(hi - 1) > get(lo))
				exchange(hi - 1, lo);
			return;
		}

		var i = lo + 1;
		var j = hi - 1;

		if (get(lo) > get(i))
			exchange(i, lo);
		if (get(j) > get(lo))
			exchange(lo, j);
		if (get(lo) > get(i))
			exchange(i, lo);

		var pivot = get(lo);

		while (true) {
			j--;
			while (pivot > get(j))
				j--;
			i++;
			while (get(i) > pivot)
				i++;
			if (j <= i)
				break;
			exchange(i, j);
		}
		exchange(lo, j);

		if ((j - lo) < (hi - j)) {
			quicksort(lo, j);
			quicksort(j + 1, hi);
		} else {
			quicksort(j + 1, hi);
			quicksort(lo, j);
		}
	}
}
