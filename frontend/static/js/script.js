
const TOKEN_KEY = "qltdnh_token";
const USER_KEY = "qltdnh_user";
const API_URL = "";

// =====================================
// HIỂN THỊ THÔNG TIN NGƯỜI DÙNG
// =====================================
function hienThiNguoiDung() {
    let user = {};

    try {
        user = JSON.parse(localStorage.getItem(USER_KEY) || "{}");
    } catch (error) {
        console.error("Lỗi đọc thông tin người dùng:", error);
    }

    const nameElement = document.querySelector("[data-user-name]");
    const roleElement = document.querySelector("[data-user-role]");
    const avatarElement = document.querySelector(".avatar");

    const hoTen = user.HoTen || user.TenDangNhap || "Người dùng";
    const vaiTro = String(user.VaiTro || "").toLowerCase().trim();

    let tenVaiTro = "Khách hàng";

    if (vaiTro === "admin") {
        tenVaiTro = "Quản trị viên";
    } else if (vaiTro === "user") {
        tenVaiTro = "Khách hàng";
    }

    if (nameElement) {
        nameElement.textContent = hoTen;
    }

    if (roleElement) {
        roleElement.textContent = tenVaiTro;
    }

    if (avatarElement) {
        avatarElement.textContent = hoTen.charAt(0).toUpperCase();
    }
}

// =====================================
// GỌI API
// =====================================
async function apiRequest(url, options = {}) {
    const headers = { ...(options.headers || {}) };

    const token = localStorage.getItem(TOKEN_KEY);

    if (token) {
        headers.Authorization = "Bearer " + token;
    }

    if (options.body && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(API_URL + url, {
        ...options,
        headers
    });

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error("Máy chủ trả về dữ liệu không hợp lệ.");
    }

    if (!response.ok || result.success === false) {
        if (response.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
        }

        throw new Error(result.message || "Có lỗi xảy ra khi gọi API.");
    }

    return result;
}

// =====================================
// HIỂN THỊ THÔNG BÁO
// =====================================
function showMessage(element, message, type = "danger") {
    if (!element) return;

    element.textContent = message;
    element.className = "mb-3 text-" + type;
}

// =====================================
// HÀM HỖ TRỢ
// =====================================
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, function (char) {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return entities[char];
    });
}

function isAvailable(value) {
    return value === true ||
        value === 1 ||
        value === "1" ||
        value === "true";
}

function formatPrice(value) {
    return Number(value || 0).toLocaleString("vi-VN") + " đ";
}

// =====================================
// ĐĂNG NHẬP
// =====================================
const loginForm = document.getElementById("loginForm");

if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        const message = document.getElementById("loginMessage");
        const button = loginForm.querySelector('button[type="submit"]');

        if (!username || !password) {
            showMessage(message, "Vui lòng nhập đầy đủ thông tin!");
            return;
        }

        try {
            button.disabled = true;
            button.textContent = "Đang đăng nhập...";

            const result = await apiRequest("/api/dang-nhap", {
                method: "POST",
                body: JSON.stringify({
                    TenDangNhap: username,
                    MatKhau: password
                })
            });

            // Backend trả token ở result.token
            // Thông tin người dùng nằm ở result.data
            const token = result.token;
            const user = result.data || {};

            if (!token) {
                throw new Error("Không nhận được token đăng nhập.");
            }

            if (!user.VaiTro) {
                throw new Error("Backend chưa trả về vai trò người dùng.");
            }

            // Xóa thông tin đăng nhập cũ
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);

            // Lưu thông tin đăng nhập mới
            localStorage.setItem(TOKEN_KEY, token);
            localStorage.setItem(USER_KEY, JSON.stringify(user));

            showMessage(message, "Đăng nhập thành công!", "success");

            window.location.href = "/";

        } catch (error) {
            showMessage(message, error.message);
        } finally {
            button.disabled = false;
            button.textContent = "Đăng nhập";
        }
    });
}

// =====================================
// TẢI DANH MỤC
// =====================================
async function loadCategories(selectElement, includeAll = false) {
    if (!selectElement) return;

    selectElement.innerHTML = "";

    const firstOption = document.createElement("option");
    firstOption.value = "";
    firstOption.textContent = includeAll
        ? "Tất cả danh mục"
        : "Đang tải danh mục...";

    selectElement.appendChild(firstOption);

    try {
        const result = await apiRequest("/api/danh-muc");
        const categories = result.data || [];

        selectElement.innerHTML = "";

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = includeAll
            ? "Tất cả danh mục"
            : "Chọn danh mục";

        selectElement.appendChild(defaultOption);

        categories.forEach(function (category) {
            if (
                category.TrangThai === false ||
                Number(category.TrangThai) === 0
            ) {
                return;
            }

            const option = document.createElement("option");
            option.value = category.MaDanhMuc;
            option.textContent = category.TenDanhMuc;

            selectElement.appendChild(option);
        });

        return categories;

    } catch (error) {
        console.error("Lỗi tải danh mục:", error);

        selectElement.innerHTML =
            '<option value="">Không tải được danh mục</option>';

        return [];
    }
}

// =====================================
// QUẢN LÝ DANH SÁCH MÓN ĂN
// =====================================
const foodTableBody = document.getElementById("foodTableBody");

if (foodTableBody) {
    let allFoods = [];

    const foodSearch = document.getElementById("foodSearch");
    const categoryFilter = document.getElementById("categoryFilter");
    const statusFilter = document.getElementById("statusFilter");

    const totalFoods = document.getElementById("totalFoods");
    const availableFoods = document.getElementById("availableFoods");
    const unavailableFoods = document.getElementById("unavailableFoods");
    const totalCategories = document.getElementById("totalCategories");
    const resultCount = document.getElementById("resultCount");

    // Cập nhật thống kê
    function updateStatistics() {
        const available = allFoods.filter(food =>
            isAvailable(food.ConKinhDoanh)
        ).length;

        const unavailable = allFoods.length - available;

        if (totalFoods) totalFoods.textContent = allFoods.length;
        if (availableFoods) availableFoods.textContent = available;
        if (unavailableFoods) unavailableFoods.textContent = unavailable;
    }

    // Hiển thị bảng món ăn
    function renderFoods(foods) {
        foodTableBody.innerHTML = "";

        if (foods.length === 0) {
            foodTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-muted">
                        Không tìm thấy món ăn phù hợp.
                    </td>
                </tr>
            `;

            if (resultCount) {
                resultCount.textContent = "Không có món ăn nào.";
            }

            return;
        }

        foods.forEach(function (food) {
            const available = isAvailable(food.ConKinhDoanh);

            const statusHTML = available
                ? '<span class="badge bg-success">Đang phục vụ</span>'
                : '<span class="badge bg-danger">Ngừng phục vụ</span>';

            const row = document.createElement("tr");

            row.innerHTML = `
                <td class="ps-3">${escapeHTML(food.MaMon || "")}</td>

                <td>
                    <span class="fw-semibold">
                        ${escapeHTML(food.TenMonAn || "")}
                    </span>
                    ${
                        food.MoTa
                            ? `<br><small class="text-muted">${escapeHTML(food.MoTa)}</small>`
                            : ""
                    }
                </td>

                <td>${escapeHTML(food.TenDanhMuc || "Chưa phân loại")}</td>

                <td class="fw-semibold text-primary">
                    ${formatPrice(food.Gia)}
                </td>

                <td>${statusHTML}</td>

                <td>
                    <a
                        href="/foods/edit/${encodeURIComponent(food.MaMonAn)}"
                        class="btn btn-sm btn-outline-primary"
                    >
                        Sửa
                    </a>
                </td>
            `;

            foodTableBody.appendChild(row);
        });

        if (resultCount) {
            resultCount.textContent =
                `Đang hiển thị ${foods.length} / ${allFoods.length} món ăn`;
        }
    }

    // Tìm kiếm và lọc món ăn
    function filterFoods() {
        const keyword = foodSearch
            ? foodSearch.value.trim().toLowerCase()
            : "";

        const selectedCategory = categoryFilter
            ? categoryFilter.value
            : "";

        const selectedStatus = statusFilter
            ? statusFilter.value
            : "";

        const filteredFoods = allFoods.filter(function (food) {
            const searchText = [
                food.MaMon,
                food.TenMonAn,
                food.TenDanhMuc
            ].join(" ").toLowerCase();

            const matchKeyword = searchText.includes(keyword);

            const matchCategory = !selectedCategory ||
                String(food.MaDanhMuc) === selectedCategory;

            const available = isAvailable(food.ConKinhDoanh);

            const matchStatus =
                !selectedStatus ||
                (selectedStatus === "available" && available) ||
                (selectedStatus === "unavailable" && !available);

            return matchKeyword && matchCategory && matchStatus;
        });

        renderFoods(filteredFoods);
    }

    // Tải danh sách món ăn từ SQL Server thông qua API
    async function loadFoods() {
        foodTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    Đang tải dữ liệu món ăn...
                </td>
            </tr>
        `;

        try {
            const result = await apiRequest("/api/mon-an");

            allFoods = Array.isArray(result.data) ? result.data : [];

            updateStatistics();
            filterFoods();

        } catch (error) {
            console.error("Lỗi tải món ăn:", error);

            foodTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger py-4">
                        Không tải được danh sách món ăn:
                        ${escapeHTML(error.message)}
                    </td>
                </tr>
            `;

            if (resultCount) {
                resultCount.textContent = "Lỗi tải dữ liệu.";
            }
        }
    }

    // Gắn sự kiện tìm kiếm và lọc
    if (foodSearch) {
        foodSearch.addEventListener("input", filterFoods);
    }

    if (categoryFilter) {
        categoryFilter.addEventListener("change", filterFoods);
    }

    if (statusFilter) {
        statusFilter.addEventListener("change", filterFoods);
    }

    // Tải danh mục và món ăn
    async function initializeFoodPage() {
        const categories = await loadCategories(categoryFilter, true);

        if (totalCategories) {
            totalCategories.textContent = (categories || []).filter(
                category => category.TrangThai !== false &&
                    Number(category.TrangThai) !== 0
            ).length;
        }

        await loadFoods();
    }

    initializeFoodPage();
}

// =====================================
// THÊM MÓN ĂN
// =====================================
const addFoodForm = document.getElementById("addFoodForm");

if (addFoodForm) {
    const categorySelect = document.getElementById("foodCategory");
    const imageInput = document.getElementById("foodImage");
    const imagePreview = document.getElementById("imagePreview");
    const removeImageButton = document.getElementById("removeImage");
    const saveButton = document.getElementById("saveFoodButton");

    let imageData = null;

    loadCategories(categorySelect);

    // Xem trước ảnh
    if (imageInput) {
        imageInput.addEventListener("change", function () {
            const file = imageInput.files[0];

            if (!file) return;

            if (file.size > 5 * 1024 * 1024) {
                alert("Ảnh không được vượt quá 5MB.");
                imageInput.value = "";
                return;
            }

            const allowedTypes = [
                "image/jpeg",
                "image/png",
                "image/webp"
            ];

            if (!allowedTypes.includes(file.type)) {
                alert("Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP.");
                imageInput.value = "";
                return;
            }

            const reader = new FileReader();

            reader.onload = function (event) {
                imageData = event.target.result;

                if (imagePreview) {
                    imagePreview.src = imageData;
                    imagePreview.style.display = "block";
                }

                if (removeImageButton) {
                    removeImageButton.style.display = "inline-block";
                }
            };

            reader.readAsDataURL(file);
        });
    }

    // Xóa ảnh
    if (removeImageButton) {
        removeImageButton.addEventListener("click", function () {
            imageData = null;

            if (imageInput) imageInput.value = "";

            if (imagePreview) {
                imagePreview.src = "";
                imagePreview.style.display = "none";
            }

            removeImageButton.style.display = "none";
        });
    }

    // Gửi dữ liệu thêm món ăn
    addFoodForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const maMon = document.getElementById("foodCode").value.trim();
        const tenMonAn = document.getElementById("foodName").value.trim();
        const maDanhMuc = categorySelect.value;
        const gia = Number(document.getElementById("foodPrice").value);
        const moTa = document.getElementById("foodDescription").value.trim();

        if (!maMon || !tenMonAn || !maDanhMuc || !gia || gia <= 0) {
            alert("Vui lòng nhập đầy đủ thông tin hợp lệ.");
            return;
        }

        const payload = {
            MaMon: maMon,
            TenMonAn: tenMonAn,
            MaDanhMuc: Number(maDanhMuc),
            Gia: gia,
            MoTa: moTa,
            HinhAnh: imageData,
            ConKinhDoanh: true
        };

        try {
            saveButton.disabled = true;
            saveButton.textContent = "Đang lưu...";

            await apiRequest("/api/mon-an", {
                method: "POST",
                body: JSON.stringify(payload)
            });

            alert("Thêm món ăn thành công!");
            window.location.href = "/foods";

        } catch (error) {
            alert(error.message);
        } finally {
            saveButton.disabled = false;
            saveButton.textContent = "Lưu món ăn";
        }
    });
}

// =====================================
// KHỞI TẠO
// =====================================
document.addEventListener("DOMContentLoaded", function () {
    hienThiNguoiDung();
});
