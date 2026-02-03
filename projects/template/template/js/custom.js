$(document).ready(function(){
  setTimeout(() => {
    $('.table-sliding').show(400)
  }, 300);
})

// sidebar
// لتغيير اتجاه ايقونة السهم الخاصة بالقائمة الموجودة في السايدبار
$("#main_sidebar .menu-title").on("click", function (e) {
  e.preventDefault();
  e.stopPropagation();

  let clicked_element = $(e.target);
  let other_menus = $("#main_sidebar .menu-title").not(this);

  other_menus = $.map(other_menus, function (value, key) {
    return [value];
  });
  //   console.log(other_menus);

  other_menus.forEach((menu) => {
    $(menu).find(".chevron-icon").first().removeClass("rotate-minus-90");
  });

  let if_expand = $(this).attr("aria-expanded");

  JSON.parse(if_expand)
    ? $(this).find(".chevron-icon").addClass("rotate-minus-90")
    : $(this).find(".chevron-icon").removeClass("rotate-minus-90");
});

// for toggeling sidebar when click on the toggline icon at the site header
// $("#toggle_sidebar").on("click", function (e) {
//   e.preventDefault();
//   e.stopPropagation();

//   let sidebar = $("#main_sidebar");

//   if (window.innerWidth > 991) {
//     if (sidebar.innerWidth() > 0) {
//       sidebar.css({
//         width: 0,
//         overflow: "hidden",
//       });
//       $(".whole-content").css("margin-right", 0);
//       $("#toggle_sidebar")
//         .removeClass("bi-text-indent-left")
//         .addClass("bi-text-indent-right");
//     } else {
//       sidebar.css("width", 260);
//       $(".whole-content").css("margin-right", "260px");
//       $("#toggle_sidebar")
//         .removeClass("bi-text-indent-right")
//         .addClass("bi-text-indent-left");
//     }
//   } else {
//     sidebar.toggleClass("d-none");
//   }
// });

/* وزارة التنمية */

// for toggeling sidebar when click on the toggline icon at the site header
$("#toggle_sidebar").on("click", function (e) {
  e.preventDefault();
  e.stopPropagation();

  let sidebar = $("#main_sidebar");

  if (window.innerWidth > 991) {
    if (sidebar.hasClass("show")) {
      sidebar.removeClass("show");
      $(".whole-content").css("margin-right", 0);
      $(this)
        .removeClass("bi-text-indent-left")
        .addClass("bi-text-indent-right");
    } else {
      sidebar.addClass("show");
      $(".whole-content").css("margin-right", "260px");
      $(this)
        .removeClass("bi-text-indent-right")
        .addClass("bi-text-indent-left");
    }
  } else {
    sidebar.toggleClass("d-none");
  }
});

document.addEventListener("click", (event) => {
  const target = event.target;
  const sidebar = document.getElementById("main_sidebar");
  if (target !== sidebar) {
    sidebar.classList.add("d-none");
  }
});

// this function to replace any unwanted result with a specific string. example: ----> replace 0 to "no data found"
function replaceResult(comparing_string, comming_result, wanted) {
  console.log(typeof comparing_string, typeof comming_result, comparing_string==comming_result);
  if (comparing_string == comming_result) {
    return wanted;
  }
  return comming_result;
}


function slide_animation(selector, dir="right"){
  $(selector).parents(".dataTables_wrapper").first().hide().show("slide", {
    direction: dir
  }, 1000);
}

function custom_validate(obj){

  const my_rules = ['required']

  $.each( obj, function( key, value ) {
    let rules = obj.rules

    $.each( rules, function( field_id, rule ) {
      if(my_rules.includes(rule)){
        check_validate(field_id, rule, obj?.fields)
      }else{
        showToast("msg-danger", `This validation ${rule} not found`)
      }
    });

  });
}

function check_validate(field_id, rule, fields_name){
  switch (rule){
    case 'required': 
      if (!$(field_id).val()) {
        $(field_id).css({"border": "1px solid red"});
        showToast("msg-danger", `الحقل ${fields_name[field_id] ? '('+fields_name[field_id]+')' : ''} مطلوب`)
      }
      break;
    default: return false;
  }
}



// $("#enrol_form").validate({
//   rules: {
//       ssn: "required",
//       father_ssn: "required",
//       mother_ssn: "required",

//   },
//   messages: {
//       ssn: "أدخل هوية الطالب",
//       father_ssn: "ادخل هوية الاب",
//       mother_ssn: "ادخل هوية الام",
//   },
// });
// }

function emptyFields(arr){
  arr.forEach(selector => {
    let element = $(selector);
    let tag = element?.prop("tagName")?.toLowerCase()

    if (tag == 'label') {
      element.text("")
    }else if(tag == 'input' && element.attr("type") == 'checkbox'){
      element.removeAttr('checked');
    }else{
      element.val("")
    }

  });



}




  //   --------------------------------------------------------------------------------------------
  //   --------------------------------------------------------------------------------------------

  let select_btn = `
  <div class="d-flex justify-content-between">
    <button class="btn btn-sm border-right border-light flex-grow-1" id="selectAllBtn" style="border-radius: 0; background-color: #f0f0f0; border-start-start-radius: .375rem;">تحديد الكل</button>
    <button class="btn btn-sm border-left border-light flex-grow-1" id="unselectAllBtn" style="border-radius: 0; background-color: #f0f0f0; border-start-end-radius: .375rem;">إلغاء تحديد الكل</button>
  </div>
`

  $(".aboslama-dropdown .dropdown-menu").prepend(select_btn)
  // Handle "Select All" button click
  $(".aboslama-dropdown #selectAllBtn").click(function(e) {
    e.stopPropagation();
    e.preventDefault();
    $(this).parents(".aboslama-dropdown").find(".dropdown-checkbox-items input[type='checkbox']").prop("checked", true);
  });

  // Handle "Unselect All" button click
  $(".aboslama-dropdown #unselectAllBtn").click(function(e){
    e.stopPropagation();
    e.preventDefault();
    $(this).parents(".aboslama-dropdown").find(".dropdown-checkbox-items input[type='checkbox']").prop("checked", false);
  });

  // to prevent colsing the dropdown
  $(".aboslama-dropdown .dropdown-item").on("click", function(e){
    e.stopPropagation()
  })


  $('.aboslama-dropdown, .aboslama-dropdown #selectAllBtn, .aboslama-dropdown #unselectAllBtn').on("click", function(){
    let select = (this.id == "selectAllBtn" || this.id == "unselectAllBtn") ? $(this).parents(".aboslama-dropdown").first() : $(this);
    let select_wrapper = select.find("button.form-select").first();
    let result = '';
    selected_items = select.find("input[type='checkbox']:checked").parent() ?? [];

    // اذا لم يتم اختيار اي عنصر
    if (selected_items.length == 0) {      
      select_wrapper.text('-- حدد --');
    }
    // اذا تم اختيار عنصر واحد
    else if (selected_items.length == 1) {      
      select_wrapper.text(selected_items.text());
    }
    // اذا تم اختيار اكثر من عنصر
    else if (selected_items.length > 1) {
      for (let index = 0; index < selected_items.length; index++) {
        result += $(selected_items[index]).text();
        // يتم وضع الفاصلة طالما لم يصل للعنصر الاخير
        if (index != selected_items.length - 1) {
          result += ', ';
        }
      }
      select_wrapper.text(result);
    }
  })


  // get the dropdown value
  function aboslama_select_get_val(selector){
    let data = [], items;
    items = $(selector + " input[type='checkbox']:checked");

    for (let index = 0; index < items.length; index++) {
      const ele = items[index];
      data.push(ele.value);
    }
    return data;
  }

  // show the select value on it's label
  // function aboslama_select_set_label(selector){
  //   let data = [], items;
  //   items = $(selector + " input[type='checkbox']:checked");

  //   for (let index = 0; index < items.length; index++) {
  //     const ele = items[index];
  //     data.push(ele.value);
  //   }
  //   return data;
  // }

  function aboslama_select_set_val(selector, options = null, values = null){
    $('.dropdown-menu').css('width', '100%');  //added by m.mnsra
    if (options != null) {
      $(selector + " > .dropdown-menu > .dropdown-checkbox-items").html(options);
    }

    let items = $(`${selector} input[type='checkbox']`);
    let select_label = '';

    if (values != null) { 
      for (let index = 0; index < items.length; index++) {         
        const ele = items[index];
        if (values.includes(ele.value)) {
          $(ele).prop("checked", true);
          select_label += $(ele).parent().text().trim().replace(/"/g, '');
          if(index < items.length -1){
            select_label += ', ';
          }
        }
      }
      $(selector + " > button.form-select").text(select_label);
    }

    return
  }

//   --------------------------------------------------------------------------------------------
//   --------------------------------------------------------------------------------------------
